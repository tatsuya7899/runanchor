"""Execution drivers: the seam between runanchor and the sandbox provider.

DriverIF (injection point):
    run(command, cwd, files, shell_mode, disposable) -> OperationRecord
    use(image) -> None
    events(operation_uuid) -> list[dict]
    close() -> None   (release the driver's session; best-effort cleanup)

ContreeDriver shells out to the `contree` CLI (host-side; agents never run
`contree auth`). DemoDriver replays recorded fixture ops so --demo needs no
network or credentials.

Live-validated 2026-09-30 (tech validation #0 — see research/contree-notes):
- ConTree is session-scoped: `contree -S <key>` binds every call; a
  non-disposable run checkpoints a new result image on the session history.
- `run -o json` returns one flat object carrying uuid, status, exit_code,
  stdout, stderr, result_image_uuid, duration, image_size, error (stdout is
  the bare string; also nested under metadata.result.*.value).
- `op show` returns the same fields flat, except the sandbox result sits at
  result.{stdout, stderr, state.{exit_code, timed_out}}. The parser accepts
  both shapes.
- Disposable (-D) runs return result_image_uuid=null (no checkpoint) —
  verify replays run non-disposable inside their own session instead.
- cwd maps to `-C <dir>`; shell mode to `-s` (the CLI joins args into
  `sh -c` itself — never wrap manually).
- Provider `status` is the orchestration outcome (SUCCESS/FAILED) and stays
  separate from the sandbox process's `exit_code` (run -- false returns
  status=SUCCESS, exit_code=1).
- Infra failures (missing binary, timeout, unparseable output, no uuid)
  degrade to a DRIVER_ERROR record rather than raising — a failed attempt
  is still a receipt (FR-1).
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

    def close(self) -> None: ...


class ContreeDriver:
    """Thin wrapper over `contree -S <session>` (subprocess, JSON mode)."""

    is_demo = False

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
        """Raw subprocess call; None on infra-level failure (no binary, timeout).

        Global flags (-S session, -o json) precede the subcommand, per the
        ConTree CLI contract.
        """
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
        # Resolve the caller's tag/name to the concrete image UUID so receipts
        # anchor to a stable identifier (`session show` reports the bound
        # image's UUID on the last history entry).
        self.current_image = self._resolve_image() or image

    def _resolve_image(self) -> str | None:
        proc = self._invoke(["-o", "json", "session", "show"])
        if proc is None or proc.returncode != 0:
            return None
        image = None
        for line in (proc.stdout or "").splitlines():
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("image"):
                image = entry["image"]
        return image

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

        args = ["-o", "json", "run"]
        if disposable:
            args.append("-D")
        if cwd and cwd != "/":
            args += ["-C", cwd]
        if shell_mode:
            args.append("-s")
        for f in files or []:
            args += ["--file", f]
        # -s makes the CLI join the argv into `sh -c` itself — the command
        # goes through as a single string; direct mode keeps separate argv.
        args += ["--", command] if shell_mode else ["--"] + shlex.split(command)

        start_image = self.current_image
        proc = self._invoke(args)
        if proc is None:
            return self._degraded(command, cwd, files,
                                  "contree invocation failed (missing binary or timeout)",
                                  shell_mode=shell_mode)

        run_raw = _try_json(proc.stdout)
        if not isinstance(run_raw, dict):
            run_raw = None
        op_uuid = run_raw.get("uuid") if run_raw else None
        anchor_source = "run-json" if op_uuid else "head"

        # The run envelope already carries the full op record; only hit
        # `op show` when the run output was unparseable or lacks fields.
        fields = _extract(run_raw) if run_raw else {}
        if not op_uuid or fields.get("exit_code") is None:
            show = self._invoke(
                ["-o", "json", "op", "show", op_uuid or "HEAD"])
            if show is not None and show.returncode == 0:
                show_fields = _extract(_try_json(show.stdout))
                for k, v in show_fields.items():
                    if fields.get(k) is None:
                        fields[k] = v
                if not op_uuid:
                    op_uuid = show_fields.get("uuid")
            if op_uuid:
                fields["uuid"] = op_uuid  # never lose the spawn-captured uuid

        if proc.returncode != 0 and not fields.get("uuid") and run_raw is None:
            return self._degraded(
                command, cwd, files,
                f"contree run rc={proc.returncode}: {proc.stderr.strip() or 'no stderr'}",
                shell_mode=shell_mode,
            )

        # When the run output wasn't JSON, the raw stdout IS the sandbox's —
        # it outranks anything op show might report for a different op.
        if not run_raw and proc.returncode == 0:
            fields["stdout"] = proc.stdout

        result_image = fields.get("result_image_uuid") or fields.get("image") or None
        if result_image:
            self.current_image = result_image

        rec = self._make_record(fields, command, cwd, shell_mode, files,
                                start_image, result_image)
        return replace(rec, anchor_source=anchor_source)

    @staticmethod
    def _make_record(fields: dict, command: str, cwd: str, shell_mode: bool,
                     files, start_image, result_image) -> OperationRecord:
        warnings: list[str] = []
        if not fields.get("uuid"):
            warnings.append("op record has no uuid — provider anchor missing")
        if fields.get("exit_code") is None:
            warnings.append("exit_code missing in op record")
        return OperationRecord(
            operation_uuid=fields.get("uuid"),
            image_uuid=start_image,
            result_image_uuid=result_image,
            command=command,
            cwd=cwd,
            shell_mode=shell_mode,
            status=fields.get("status") or "UNKNOWN",
            exit_code=fields.get("exit_code"),
            stdout=str(fields.get("stdout") or ""),
            stderr=str(fields.get("stderr") or ""),
            diff_sha256=None,
            files=list(files or []),
            duration_s=fields.get("duration"),
            consumed_cpu_s=fields.get("consumed_cpu"),
            consumed_memory=fields.get("consumed_memory"),
            consumed_memory_unit=fields.get("consumed_memory_unit"),
            parse_warnings=warnings,
        )

    @staticmethod
    def _degraded(command, cwd, files, note: str, shell_mode: bool = False) -> OperationRecord:
        """An execution attempt with no provider record still gets recorded —
        marked DRIVER_ERROR so it can never masquerade as a real run."""
        return OperationRecord(
            operation_uuid=None, image_uuid=None, result_image_uuid=None,
            command=command, cwd=cwd, shell_mode=shell_mode,
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

    def close(self) -> None:
        """Release this driver's session (best-effort; never raises)."""
        try:
            self._invoke(["session", "delete", self.session, "-y"])
        except Exception:
            pass


def _try_json(text: str):
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


def _unwrap(value):
    """ConTree nests stream payloads as {"value": ..., "encoding": ...} under
    metadata.result.* while op show returns bare strings — accept both."""
    if isinstance(value, dict):
        return value.get("value")
    return value


def _extract(raw: dict | None) -> dict:
    """Flatten the `run -o json` envelope and `op show` shape into one field
    set. Live-measured 2026-09-30; see research notes §6 for raw examples."""
    if not isinstance(raw, dict):
        return {}
    res = raw.get("result") or {}
    meta_res = (raw.get("metadata") or {}).get("result") or {}
    state = res.get("state") or meta_res.get("state") or {}
    stdout = raw.get("stdout")
    if stdout is None:
        stdout = _unwrap(res.get("stdout")) or _unwrap(meta_res.get("stdout"))
    stderr = raw.get("stderr")
    if stderr is None:
        stderr = _unwrap(res.get("stderr")) or _unwrap(meta_res.get("stderr"))
    exit_code = raw.get("exit_code")
    if exit_code is None:
        exit_code = state.get("exit_code", res.get("exit_code"))
    return {
        "uuid": raw.get("uuid"),
        "status": raw.get("status"),
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "result_image_uuid": raw.get("result_image_uuid"),
        "image": raw.get("image"),
        "duration": raw.get("duration"),
        "timed_out": state.get("timed_out"),
        "error": raw.get("error"),
        "image_size": raw.get("image_size"),
        "consumed_cpu": raw.get("consumed_cpu"),
        "consumed_memory": raw.get("consumed_memory"),
        "consumed_memory_unit": raw.get("consumed_memory_unit"),
    }


class DemoDriver:
    """Replays recorded fixture ops; implements the same Driver IF.

    Records are force-marked demo=True so a fixture can never masquerade as a
    live run regardless of caller wiring (FR-6).
    """

    def __init__(self, ops: list[dict], event_map: dict | None = None):
        self._ops = [
            OperationRecord(**{**o, "demo": True, "anchor_source": "demo"})
            for o in ops
        ]
        self._events = event_map or {}
        self.current_image: str | None = None

    is_demo = True

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

    def close(self) -> None:
        """No live session to release — present for Driver parity."""
