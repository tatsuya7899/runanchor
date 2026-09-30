"""Driver seam tests: DemoDriver fixture replay + ContreeDriver CLI wrapping.

Live schema as measured 2026-09-30 (research/contree-notes_runanchor_20260929.md
§4): `run -o json` returns flat fields plus a nested metadata.result copy;
`op show` returns flat fields plus result.{stdout,stderr,state.*}.
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

    def test_close_is_noop(self, tmp_path):
        """Driver parity: verify always calls close(); demo has no session."""
        d = DemoDriver.from_dir(write_fixture(tmp_path, [OP]))
        d.close()  # must not raise


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


# --- real ConTree payload shapes, measured 2026-09-30 ----------------------

RUN_JSON = {  # `contree -o json run -- echo hello-runanchor` (non-disposable)
    "uuid": "01a0f146-0000-7000-8000-000000000001",
    "kind": "instance",
    "status": "SUCCESS",
    "duration": 1.298,
    "image_size": 926,
    "result_image_uuid": "b2516231-0000-7000-8000-00000000000b",
    "metadata": {
        "result": {
            "stdout": {"value": "hello-runanchor\n", "encoding": "ascii",
                        "truncated": False},
            "stderr": {"value": "", "encoding": "ascii", "truncated": False},
            "state": {"exit_code": 0, "timed_out": False},
        }
    },
    "result": {"image": "b2516231-0000-7000-8000-00000000000b", "tag": None},
    "exit_code": 0,
    "image": "b2516231-0000-7000-8000-00000000000b",
    "tag": "",
    "stdout": "hello-runanchor\n",
    "stderr": "",
    "error": "",
}

OP_SHOW_JSON = {  # `contree -o json op show <uuid>`
    "uuid": "01a0f146-0000-7000-8000-000000000001",
    "status": "SUCCESS",
    "exit_code": 0,
    "duration": 0.438,
    "result_image_uuid": "b2516231-0000-7000-8000-00000000000b",
    "kind": "instance",
    "image_size": 0,
    "image": "b2516231-0000-7000-8000-00000000000b",
    "tag": "",
    "error": "",
    "result": {
        "stdout": "hello-runanchor\n",
        "stderr": "",
        "state": {"exit_code": 0, "timed_out": False},
    },
}

DISPOSABLE_JSON = {  # `run -D` — no checkpoint is created
    "uuid": "01a0f147-0000-7000-8000-000000000002",
    "kind": "instance",
    "status": "SUCCESS",
    "duration": 0.742,
    "image_size": -1,
    "result_image_uuid": None,
    "result": {"image": None, "tag": None},
    "exit_code": 0,
    "image": "",
    "stdout": "hello-disposable\n",
    "stderr": "",
    "error": "",
}


class TestContreeDriver:
    def test_use_invokes_cli_and_resolves_image_uuid(self):
        """use() binds the image, then `session show` resolves the tag/name
        to the concrete image UUID recorded on receipts."""
        session_show = json.dumps(
            {"id": 1, "kind": "use", "image": "img-uuid-resolved",
             "title": "tag:python:3.12-slim"})
        runner = FakeRunner([(0, "", ""), (0, session_show, "")])
        d = ContreeDriver(session="s1", contree_bin="contree", runner=runner)
        d.use("tag:python:3.12-slim")
        assert runner.calls[0] == ["contree", "-S", "s1", "use",
                                   "tag:python:3.12-slim"]
        assert runner.calls[1][:3] == ["contree", "-S", "s1"]
        assert "session" in runner.calls[1] and "show" in runner.calls[1]
        assert d.current_image == "img-uuid-resolved"

    def test_use_falls_back_to_passed_image_when_unresolvable(self):
        runner = FakeRunner([(0, "", ""), (1, "", "boom")])
        d = ContreeDriver(session="s1", runner=runner)
        d.use("img-x")
        assert d.current_image == "img-x"

    def test_run_parses_live_run_envelope(self):
        """The real `run -o json` envelope parses without an extra op show call."""
        runner = FakeRunner([(0, json.dumps(RUN_JSON), "")])
        d = ContreeDriver(session="s1", contree_bin="contree", runner=runner)
        rec = d.run("echo hello-runanchor", cwd="/work")
        assert runner.calls[0] == [
            "contree", "-S", "s1", "-o", "json", "run", "-C", "/work", "--",
            "echo", "hello-runanchor",
        ]
        assert len(runner.calls) == 1  # run JSON is complete — no op show
        assert rec.operation_uuid == RUN_JSON["uuid"]
        assert rec.anchor_source == "run-json"
        assert rec.exit_code == 0
        assert rec.stdout == "hello-runanchor\n"
        assert rec.stderr == ""
        assert rec.result_image_uuid == RUN_JSON["result_image_uuid"]
        assert rec.duration_s == 1.298
        assert rec.command == "echo hello-runanchor"

    def test_run_parses_nested_metadata_shape(self):
        """If top-level convenience fields are absent, metadata.result.*.value
        still yields exit_code/stdout/stderr."""
        nested = {
            "uuid": "op-nested",
            "status": "SUCCESS",
            "result_image_uuid": "img-nested",
            "metadata": {"result": {
                "stdout": {"value": "out\n"},
                "stderr": {"value": "err\n"},
                "state": {"exit_code": 3, "timed_out": False},
            }},
        }
        runner = FakeRunner([(0, json.dumps(nested), "")])
        d = ContreeDriver(session="s1", runner=runner)
        rec = d.run("x", cwd="/")
        assert rec.exit_code == 3
        assert rec.stdout == "out\n"
        assert rec.stderr == "err\n"

    def test_run_fills_from_op_show_flat_shape(self):
        """When the run envelope lacks fields, `op show <uuid>` fills them
        (flat result.{stdout,state.exit_code} shape)."""
        sparse = {"uuid": "op-9"}  # uuid only — fields come from op show
        runner = FakeRunner([(0, json.dumps(sparse), ""),
                             (0, json.dumps(OP_SHOW_JSON), "")])
        d = ContreeDriver(session="s1", runner=runner)
        rec = d.run("echo hi", cwd="/")
        assert runner.calls[1] == [
            "contree", "-S", "s1", "-o", "json", "op", "show", "op-9"]
        assert rec.exit_code == 0
        assert rec.stdout == "hello-runanchor\n"
        assert rec.operation_uuid == "op-9"
        assert rec.anchor_source == "run-json"

    def test_run_falls_back_to_head_when_no_uuid(self):
        """Non-JSON run output -> sandbox stdout is raw; anchor falls back to HEAD."""
        op_json = json.dumps(OP_SHOW_JSON)
        runner = FakeRunner([(0, "raw sandbox output\n", ""), (0, op_json, "")])
        d = ContreeDriver(session="s1", runner=runner)
        rec = d.run("pytest -q", cwd="/")
        assert "op" in runner.calls[1] and "HEAD" in runner.calls[1]
        assert rec.anchor_source == "head"
        assert rec.stdout == "raw sandbox output\n"
        assert rec.operation_uuid == OP_SHOW_JSON["uuid"]

    def test_disposable_run_carries_d_flag_and_null_image(self):
        """-D runs return result_image_uuid=null (live-measured) — the record
        keeps that honestly instead of inventing an image."""
        runner = FakeRunner([(0, json.dumps(DISPOSABLE_JSON), "")])
        d = ContreeDriver(session="s1", runner=runner)
        rec = d.run("echo hi", cwd="/", disposable=True)
        assert "-D" in runner.calls[0]
        assert rec.result_image_uuid is None

    def test_shell_mode_passes_command_as_single_arg_with_s_flag(self):
        """-s: the CLI joins argv into `sh -c` itself — no manual wrap."""
        runner = FakeRunner([(0, json.dumps(RUN_JSON), "")])
        d = ContreeDriver(session="s1", runner=runner)
        d.run("a | b && c", cwd="/w", shell_mode=True)
        call = runner.calls[0]
        assert "-s" in call
        assert call[-2:] == ["--", "a | b && c"]
        assert "sh" not in call and "-c" not in call

    def test_file_mounts_use_dashdash_file(self):
        runner = FakeRunner([(0, json.dumps(RUN_JSON), "")])
        d = ContreeDriver(session="s1", runner=runner)
        d.run("ls", cwd="/", files=["/h/a.py:/w/a.py", "/h/b.py:/w/b.py"])
        call = runner.calls[0]
        assert call[call.index("--file") + 1] == "/h/a.py:/w/a.py"
        assert call.count("--file") == 2

    def test_start_and_result_images_tracked_across_runs(self):
        """receipt.image_uuid is the session's image BEFORE the run; after a
        non-disposable run it becomes that run's result image."""
        session_show = json.dumps({"image": "img-base-uuid"})
        runner = FakeRunner([
            (0, "", ""), (0, session_show, ""),       # use + resolve
            (0, json.dumps(RUN_JSON), ""),            # run 1
            (0, json.dumps(RUN_JSON), ""),            # run 2
        ])
        d = ContreeDriver(session="s1", runner=runner)
        d.use("tag:x")
        r1 = d.run("cmd", cwd="/")
        r2 = d.run("cmd", cwd="/")
        assert r1.image_uuid == "img-base-uuid"
        assert r1.result_image_uuid == RUN_JSON["result_image_uuid"]
        assert r2.image_uuid == RUN_JSON["result_image_uuid"]

    def test_close_deletes_session(self):
        runner = FakeRunner([(0, "", "")])
        d = ContreeDriver(session="ra_verify_x", runner=runner)
        d.close()
        assert runner.calls[0] == [
            "contree", "-S", "ra_verify_x",
            "session", "delete", "ra_verify_x", "-y"]

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

    def test_op_show_failure_keeps_run_json_uuid(self):
        """P1-B: if `op show` fails, the uuid captured at run survives —
        losing it would silently strip the provider anchor off every run."""
        sparse = {"uuid": "op-9"}  # triggers the op show fill
        runner = FakeRunner([(0, json.dumps(sparse), ""),
                             (1, "", "op show unsupported")])
        d = ContreeDriver(session="s1", runner=runner)
        rec = d.run("pytest -q", cwd="/")
        assert rec.operation_uuid == "op-9"
        assert rec.anchor_source == "run-json"
        assert rec.parse_warnings  # missing fields are noted, not silent

    def test_failed_command_distinguishes_status_from_exit_code(self):
        """Live: `run -- false` yields status=SUCCESS (orchestration ok) with
        exit_code=1 (process failed) — the record must keep both."""
        failed = {**RUN_JSON, "uuid": "op-f", "exit_code": 1}
        runner = FakeRunner([(0, json.dumps(failed), "")])
        d = ContreeDriver(session="s1", runner=runner)
        rec = d.run("false", cwd="/")
        assert rec.status == "SUCCESS"
        assert rec.exit_code == 1

    def test_demo_driver_marks_anchor_source(self, tmp_path):
        d = DemoDriver.from_dir(write_fixture(tmp_path, [OP]))
        rec = d.run("x", cwd="/work")
        assert rec.demo is True
        assert rec.anchor_source == "demo"
        assert d.is_demo is True
        assert ContreeDriver(session="x").is_demo is False
