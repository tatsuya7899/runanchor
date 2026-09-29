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

    def test_fixture_records_are_forced_demo(self, tmp_path):
        """FR-6: a replayed fixture can never masquerade as a live run."""
        d = DemoDriver.from_dir(write_fixture(tmp_path, [OP]))
        assert d.run("x", cwd="/work").demo is True

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

    def test_run_anchors_via_run_json_uuid(self):
        """The op uuid comes from the run's own JSON output, not HEAD."""
        run_json = json.dumps({"uuid": "op-9", "stdout": "1 passed\n"})
        op_json = json.dumps({
            "uuid": "op-9", "status": "SUCCESS",
            "result": {"exit_code": 0},
            "image_uuid": "img-a", "result_image_uuid": "img-b",
            "metadata": {"command": "pytest -q"},
            "duration": 2.0,
            "consumed_cpu": 1.0, "consumed_memory": 1024,
        })
        runner = FakeRunner([(0, run_json, ""), (0, op_json, "")])
        d = ContreeDriver(session="s1", contree_bin="contree", runner=runner)
        rec = d.run("pytest -q", cwd="/work", disposable=True)
        assert runner.calls[0] == [
            "contree", "-S", "s1", "-o", "json", "run", "-D", "--",
            "sh", "-c", "cd /work && pytest -q",
        ]
        # anchored to the spawned op, not HEAD
        assert runner.calls[1] == [
            "contree", "-S", "s1", "-o", "json", "op", "show", "op-9"
        ]
        assert rec.operation_uuid == "op-9"
        assert rec.anchor_source == "run-json"
        assert rec.exit_code == 0
        assert rec.stdout == "1 passed\n"
        assert rec.command == "pytest -q"   # recorded command, not the cd wrap

    def test_run_without_cwd_uses_direct_argv(self):
        run_json = json.dumps({"uuid": "op-1"})
        op_json = json.dumps({"uuid": "op-1", "status": "SUCCESS", "result": {"exit_code": 0}})
        runner = FakeRunner([(0, run_json, ""), (0, op_json, "")])
        d = ContreeDriver(session="s1", runner=runner)
        d.run("ls -la", cwd="/")
        assert runner.calls[0][-2:] == ["ls", "-la"]

    def test_run_falls_back_to_head_when_no_uuid(self):
        """Non-JSON run output -> sandbox stdout is raw; anchor falls back to HEAD."""
        op_json = json.dumps({"uuid": "op-h", "status": "SUCCESS", "result": {"exit_code": 0}})
        runner = FakeRunner([(0, "raw sandbox output\n", ""), (0, op_json, "")])
        d = ContreeDriver(session="s1", runner=runner)
        rec = d.run("pytest -q", cwd="/")
        assert "op" in runner.calls[1] and "HEAD" in runner.calls[1]
        assert rec.anchor_source == "head"
        assert rec.stdout == "raw sandbox output\n"
        assert rec.operation_uuid == "op-h"

    def test_infra_failure_returns_degraded_record(self):
        """FR-1: even an unrecordable attempt becomes a marked record."""
        runner = FakeRunner([(1, "", "boom"), (1, "", "boom")])
        d = ContreeDriver(session="s1", runner=runner)
        rec = d.run("pytest -q", cwd="/work")
        assert rec.status == "DRIVER_ERROR"
        assert rec.operation_uuid is None
        assert rec.parse_warnings

    def test_missing_binary_returns_degraded_record(self):
        def missing(argv, **kw):
            raise FileNotFoundError("contree")

        d = ContreeDriver(session="s1", runner=missing)
        assert d.run("x", cwd="/").status == "DRIVER_ERROR"

    def test_empty_command_raises(self):
        d = ContreeDriver(session="s1", runner=FakeRunner([]))
        with pytest.raises(DriverError):
            d.run("   ", cwd="/")

    def test_op_record_missing_fields_carries_warnings(self):
        """An op record without uuid/exit_code produces a warning-bearing record."""
        runner = FakeRunner([(0, "not json", ""), (0, "{}", "")])
        d = ContreeDriver(session="s1", runner=runner)
        rec = d.run("x", cwd="/")
        assert rec.status == "UNKNOWN"
        assert any("uuid" in w for w in rec.parse_warnings)
        assert any("exit_code" in w for w in rec.parse_warnings)
