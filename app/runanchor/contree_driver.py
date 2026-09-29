"""Execution drivers: the seam between runanchor and the sandbox provider.

DriverIF (injection point):
    run(command, cwd, files, shell_mode, disposable) -> OperationRecord
    use(image) -> None
    events(operation_uuid) -> list[dict]

ContreeDriver shells out to the `contree` CLI (host-side; agents never run
`contree auth`). DemoDriver replays recorded fixture ops so --demo needs no
network or credentials.

NOTE: ContreeDriver's provider-field mapping (_parse_op) is provisional until
tech validation #0 observes a real `contree run` response shape.
"""

from __future__ import annotations

import json
import shlex
import subprocess
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
        proc = self._runner(
            [self.bin, "-S", self.session] + args,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if proc.returncode != 0:
            raise DriverError(f"contree {args[0]} failed: {proc.stderr.strip()}")
        return proc

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
        args = ["run"]
        if disposable:
            args.append("-D")
        for f in files or []:
            args += ["--file", f]
        args.append("--")
        args += ["sh", "-c", command] if shell_mode else shlex.split(command)
        proc = self._exec(args)
        return self._fetch_latest_op(proc.stdout, proc.stderr, command, cwd, shell_mode)

    def _fetch_latest_op(self, stdout: str, stderr: str, command: str, cwd: str, shell_mode: bool) -> OperationRecord:
        proc = self._exec(["-o", "json", "op", "show", "HEAD"])
        return self._parse_op(json.loads(proc.stdout or "{}"), stdout, stderr, command, cwd, shell_mode)

    def events(self, operation_uuid: str) -> list[dict]:
        proc = self._exec(["-o", "json", "op", "events", operation_uuid])
        try:
            data = json.loads(proc.stdout or "[]")
        except json.JSONDecodeError as e:
            raise DriverError(f"unparseable events payload: {e}")
        return data if isinstance(data, list) else data.get("events", [])

    @staticmethod
    def _parse_op(raw: dict, stdout: str, stderr: str, command: str, cwd: str, shell_mode: bool) -> OperationRecord:
        """Map provider op record -> OperationRecord. Field names to be
        confirmed against a live `contree op show` at tech validation #0."""
        consumed = raw.get("consumed") or {}
        return OperationRecord(
            operation_uuid=raw.get("uuid"),
            image_uuid=raw.get("image_uuid"),
            result_image_uuid=raw.get("result_image_uuid"),
            command=raw.get("command") or command,
            cwd=raw.get("cwd") or cwd,
            shell_mode=shell_mode,
            status=raw.get("status", "UNKNOWN"),
            exit_code=raw.get("exit_code"),
            stdout=stdout,
            stderr=stderr,
            diff_sha256=raw.get("diff_sha256"),
            duration_s=raw.get("duration_s"),
            consumed_cpu_s=consumed.get("cpu_s"),
            consumed_memory=consumed.get("memory"),
            consumed_memory_unit=consumed.get("memory_unit"),
        )


class DemoDriver:
    """Replays recorded fixture ops; implements the same Driver IF."""

    def __init__(self, ops: list[dict], event_map: dict | None = None):
        self._ops = [OperationRecord(**o) for o in ops]
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
