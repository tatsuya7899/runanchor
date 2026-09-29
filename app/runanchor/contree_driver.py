"""Execution drivers: the seam between runanchor and the sandbox provider.

DriverIF (injection point):
    run(command, cwd, files, shell_mode, disposable) -> OperationRecord
    use(image) -> None
    events(operation_uuid) -> list[dict]

ContreeDriver shells out to the `contree` CLI (host-side; agents never run
`contree auth`). DemoDriver replays recorded fixture ops so --demo needs no
network or credentials.

Live-uncertain points (must be re-checked at tech validation #0):
- `contree -o json run` is assumed to return the op uuid at spawn so the
  receipt anchors to the right operation (fallback: `op show HEAD`, flagged
  anchor_source="head" — weaker; concurrent ops in the same session could
  misattribute).
- Field names in `_parse_op` follow the documented contree-client models
  (result.exit_code, duration, consumed_cpu/memory flat, command under
  metadata).
- Whether a `-D` (disposable) run still reports result_image_uuid — verify's
  image-presence comparison depends on it; see verifier.py.
- Whether a failed sandbox command propagates into the CLI return code.
  run() therefore degrades to a DRIVER_ERROR record rather than losing the
  attempt (FR-1: failed attempts are receipts too).
"""

from __future__ import annotations

import json
import shlex
import subprocess
from dataclasses import replace
from pathlib import Path
from typing import Protocol

from .receipt import OperationRecord


class DriverError(Exception):
    pass


class Driver(Protocol):
    def run(
        self,
        command: str,
        cwd: str,
        files: list[str] | None = None,
        shell_mode: bool = False,
        disposable: bool = False,
    ) -> OperationRecord: ...

    def use(self, image: str) -> None: ...

    def events(self, operation_uuid: str) -> list[dict]: ...


class ContreeDriver:
    """Thin wrapper over `contree -S <session>` (subprocess, JSON mode)."""

    def __init__(self, session: str, contree_bin: str = "contree", runner=None):
        self.session = session
        self.bin = contree_bin
        self._runner = runner or subprocess.run
        self.current_image: str | None = None

    def _exec(self, args: list[str]):
        """Run a contree subcommand; raise DriverError on CLI-level failure."""
        proc = self._invoke(args)
        if proc is None:
            raise DriverError("contree invocation failed (missing binary or timeout)")
        if proc.returncode != 0:
            raise DriverError(f"contree {args[-1]} failed: {proc.stderr.strip()}")
        return proc

    def _invoke(self, args: list[str]):
        """Raw subprocess call; None on infra-level failure (no binary, timeout)."""
        try:
            return self._runner(
                [self.bin, "-S", self.session] + args,
                capture_output=True,
                text=True,
                timeout=600,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None

    def use(self, image: str) -> None:
        self._exec(["use", image])
        self.current_image = image

    def run(
        self,
        command: str,
        cwd: str,
        files: list[str] | None = None,
        shell_mode: bool = False,
        disposable: bool = False,
    ) -> OperationRecord:
        """Execute one sandbox run and anchor it to the provider op record.

        Never raises for execution-path failures — a failed attempt returns a
        degraded DRIVER_ERROR record so it still lands on the ledger.
        """
        if not command or not command.strip():
            raise DriverError("empty command")
        effective = command
        if cwd and cwd != "/":
            effective = f"cd {shlex.quote(cwd)} && {command}"
            shell_mode = True  # the cd wrap runs under sh -c
        tail = ["sh", "-c", effective] if shell_mode else shlex.split(command)

        args = ["-o", "json", "run"]
        if disposable:
            args.append("-D")
        for f in files or []:
            args += ["--file", f]
        args += ["--"] + tail

        proc = self._invoke(args)
        if proc is None:
            return self._degraded(command, cwd, files,
                                  "contree invocation failed (missing binary or timeout)")

        meta = _try_json(proc.stdout)
        op_uuid = meta.get("uuid") if isinstance(meta, dict) else None
        anchor_source = "run-json" if op_uuid else "head"

        op_raw: dict = {}
        show = self._invoke(["-o", "json", "op", "show", op_uuid or "HEAD"])
        if show is not None and show.returncode == 0:
            show_meta = _try_json(show.stdout)
            if isinstance(show_meta, dict):
                op_raw = show_meta
                if op_uuid:
                    op_raw.setdefault("uuid", op_uuid)

        if proc.returncode != 0 and not op_raw:
            return self._degraded(
                command, cwd, files,
                f"contree run rc={proc.returncode}: {proc.stderr.strip() or 'no stderr'}",
            )

        # Sandbox stdout lives in the run JSON envelope (provisional field
        # names); when the output wasn't JSON the raw stdout IS the sandbox's.
        if isinstance(meta, dict):
            sandbox_stdout = str(meta.get("stdout") or meta.get("output") or "")
        else:
            sandbox_stdout = proc.stdout if proc.returncode == 0 else ""

        rec = self._parse_op(op_raw, sandbox_stdout, proc.stderr, command, cwd,
                             shell_mode, files)
        return replace(rec, anchor_source=anchor_source)

    @staticmethod
    def _degraded(command, cwd, files, note: str) -> OperationRecord:
        """An execution attempt with no provider record still gets recorded —
        marked DRIVER_ERROR so it can never masquerade as a real run."""
        return OperationRecord(
            operation_uuid=None, image_uuid=None, result_image_uuid=None,
            command=command, cwd=cwd, shell_mode=True,
            status="DRIVER_ERROR", exit_code=None,
            stdout="", stderr=note, files=list(files or []),
            parse_warnings=[note],
        )

    def events(self, operation_uuid: str) -> list[dict]:
        proc = self._exec(["-o", "json", "op", "events", operation_uuid])
        try:
            data = json.loads(proc.stdout or "[]")
        except json.JSONDecodeError as e:
            raise DriverError(f"unparseable events payload: {e}")
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return list(data.get("events", []))
        return []

    @staticmethod
    def _parse_op(raw: dict, stdout: str, stderr: str, command: str, cwd: str,
                  shell_mode: bool, files) -> OperationRecord:
        """Map provider op record -> OperationRecord.

        Field names follow the documented contree-client model: `result`
        carries the exit code, `duration`/`consumed_cpu`/`consumed_memory` are
        flat, `command` sits under `metadata`. Re-check against a live
        `op show` at tech validation #0.
        """
        warnings: list[str] = []
        result = raw.get("result") or {}
        meta = raw.get("metadata") or {}
        exit_code = result.get("exit_code", result.get("code"))
        if raw.get("uuid") is None:
            warnings.append("op record has no uuid — provider anchor missing")
        if exit_code is None:
            warnings.append("exit_code missing in op record")
        return OperationRecord(
            operation_uuid=raw.get("uuid"),
            image_uuid=raw.get("image_uuid"),
            result_image_uuid=raw.get("result_image_uuid"),
            command=str(meta.get("command") or command),
            cwd=cwd,
            shell_mode=shell_mode,
            status=raw.get("status", "UNKNOWN"),
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            diff_sha256=raw.get("diff_sha256"),
            files=list(files or []),
            duration_s=raw.get("duration", raw.get("duration_s")),
            consumed_cpu_s=raw.get("consumed_cpu"),
            consumed_memory=raw.get("consumed_memory"),
            consumed_memory_unit=raw.get("consumed_memory_unit"),
            parse_warnings=warnings,
        )


def _try_json(text: str):
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


class DemoDriver:
    """Replays recorded fixture ops; implements the same Driver IF.

    Records are force-marked demo=True so a fixture can never masquerade as a
    live run regardless of caller wiring (FR-6).
    """

    def __init__(self, ops: list[dict], event_map: dict | None = None):
        self._ops = [OperationRecord(**{**o, "demo": True}) for o in ops]
        self._events = event_map or {}
        self.current_image: str | None = None

    @property
    def remaining(self) -> int:
        return len(self._ops)

    @classmethod
    def from_dir(cls, path) -> "DemoDriver":
        d = Path(path)
        ops = [
            json.loads(line)
            for line in (d / "ops.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        events_file = d / "events.json"
        event_map = json.loads(events_file.read_text(encoding="utf-8")) if events_file.exists() else {}
        return cls(ops, event_map)

    def use(self, image: str) -> None:
        self.current_image = image

    def run(
        self,
        command: str,
        cwd: str,
        files: list[str] | None = None,
        shell_mode: bool = False,
        disposable: bool = False,
    ) -> OperationRecord:
        if not self._ops:
            raise DriverError("demo fixture exhausted")
        return self._ops.pop(0)

    def events(self, operation_uuid: str) -> list[dict]:
        return list(self._events.get(operation_uuid, []))
