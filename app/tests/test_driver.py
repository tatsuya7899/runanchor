"""Driver seam tests: DemoDriver fixture replay + ContreeDriver CLI wrapping.

The provider field mapping in ContreeDriver is provisional until the first
live `contree run` (tech validation #0); the IF and demo path are stable.
"""

import json
from pathlib import Path

import pytest

from runanchor.contree_driver import (
    ContreeDriver,
    DemoDriver,
    DriverError,
)
from runanchor.receipt import OperationRecord

OP = dict(
    operation_uuid="op-1",
    image_uuid="img-a",
    result_image_uuid="img-b",
    command="pytest -q",
    cwd="/work",
    shell_mode=False,
    status="SUCCESS",
    exit_code=0,
    stdout="1 passed\n",
    stderr="",
    diff_sha256="b" * 64,
    duration_s=2.0,
    consumed_cpu_s=1.0,
    consumed_memory=1024,
    consumed_memory_unit="bytes",
)


def write_fixture(dir_path: Path, ops, events=None):
    dir_path.mkdir(parents=True, exist_ok=True)
    (dir_path / "ops.jsonl").write_text(
        "".join(json.dumps(o) + "\n" for o in ops), encoding="utf-8"
    )
    if events is not None:
        (dir_path / "events.json").write_text(json.dumps(events), encoding="utf-8")
    return dir_path


class TestDemoDriver:
    def test_run_replays_ops_in_order(self, tmp_path):
        d = DemoDriver.from_dir(write_fixture(tmp_path, [OP, {**OP, "operation_uuid": "op-2"}]))
        d.use("img-a")
        first = d.run("pytest -q", cwd="/work", disposable=True)
        second = d.run("pytest -q", cwd="/work", disposable=True)
        assert first.operation_uuid == "op-1"
        assert second.operation_uuid == "op-2"
        assert isinstance(first, OperationRecord)

    def test_exhaustion_raises(self, tmp_path):
        d = DemoDriver.from_dir(write_fixture(tmp_path, [OP]))
        d.run("x", cwd="/work")
        with pytest.raises(DriverError):
            d.run("x", cwd="/work")

    def test_use_records_selected_image(self, tmp_path):
        d = DemoDriver.from_dir(write_fixture(tmp_path, [OP]))
        d.use("img-base")
        assert d.current_image == "img-base"

    def test_events_from_fixture(self, tmp_path):
        d = DemoDriver.from_dir(
            write_fixture(tmp_path, [OP], events={"op-1": [{"kind": "exit", "code": 0}]})
        )
        d.run("x", cwd="/work")
        assert d.events("op-1") == [{"kind": "exit", "code": 0}]
        assert d.events("op-unknown") == []


class FakeRunner:
    """Captures argv and replays canned subprocess results."""

    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def __call__(self, argv, **kw):
        self.calls.append(argv)

        class Proc:
            pass

        rc, out, err = self.results.pop(0)
        p = Proc()
        p.returncode, p.stdout, p.stderr = rc, out, err
        return p


class TestContreeDriver:
    def test_use_invokes_cli(self):
        runner = FakeRunner([(0, "", "")])
        d = ContreeDriver(session="s1", contree_bin="contree", runner=runner)
        d.use("img-x")
        assert runner.calls[0] == ["contree", "-S", "s1", "use", "img-x"]

    def test_run_then_fetch_op(self):
        op_json = json.dumps(
            {
                "uuid": "op-9",
                "status": "SUCCESS",
                "exit_code": 0,
                "image_uuid": "img-a",
                "result_image_uuid": "img-b",
                "command": "pytest -q",
                "duration_s": 2.0,
                "consumed": {"cpu_s": 1.0, "memory": 1024, "memory_unit": "bytes"},
            }
        )
        runner = FakeRunner([(0, "1 passed\n", ""), (0, op_json, "")])
        d = ContreeDriver(session="s1", contree_bin="contree", runner=runner)
        rec = d.run("pytest -q", cwd="/work", disposable=True)
        assert runner.calls[0] == [
            "contree", "-S", "s1", "run", "-D", "--", "pytest", "-q",
        ]
        assert runner.calls[1] == [
            "contree", "-S", "s1", "-o", "json", "op", "show", "HEAD"
        ]
        assert isinstance(rec, OperationRecord)
        assert rec.operation_uuid == "op-9"
        assert rec.exit_code == 0
        assert rec.stdout == "1 passed\n"

    def test_run_shell_mode_wraps_in_sh(self):
        runner = FakeRunner([(0, "", ""), (0, "{}", "")])
        d = ContreeDriver(session="s1", runner=runner)
        d.run("echo hi && true", cwd="/work", shell_mode=True)
        assert runner.calls[0][-3:] == ["sh", "-c", "echo hi && true"]

    def test_cli_failure_raises_driver_error(self):
        runner = FakeRunner([(1, "", "boom")])
        d = ContreeDriver(session="s1", runner=runner)
        with pytest.raises(DriverError):
            d.run("x", cwd="/work")

    def test_failed_run_returns_failure_record(self):
        """FR-1: a failed sandbox run still yields a record, not an exception."""
        op_json = json.dumps({"uuid": "op-bad", "status": "FAILURE", "exit_code": 1})
        runner = FakeRunner([(0, "", "failing\n"), (0, op_json, "")])
        d = ContreeDriver(session="s1", runner=runner)
        rec = d.run("pytest -q", cwd="/work")
        assert rec.status == "FAILURE"
        assert rec.exit_code == 1
