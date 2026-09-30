"""Acceptance S9: the autonomous loop issues one receipt per run, in series."""

import json

import pytest

from runanchor.agent_loop import NemotronPlanner, ScriptedPlanner, run_loop
from runanchor.contree_driver import DemoDriver
from runanchor.ledger import Ledger
from runanchor.receipt import OperationRecord, issue_receipt

OPS = [
    dict(operation_uuid="op-1", image_uuid="i0", result_image_uuid="i1",
         command="pytest -q", cwd="/work", shell_mode=False, status="FAILURE",
         exit_code=1, stdout="1 failed\n", stderr=""),
    dict(operation_uuid="op-2", image_uuid="i1", result_image_uuid="i2",
         command="pytest -q", cwd="/work", shell_mode=False, status="FAILURE",
         exit_code=1, stdout="1 failed\n", stderr=""),
    dict(operation_uuid="op-3", image_uuid="i2", result_image_uuid="i3",
         command="pytest -q", cwd="/work", shell_mode=False, status="SUCCESS",
         exit_code=0, stdout="1 passed\n", stderr=""),
]


@pytest.fixture
def ledger(tmp_path):
    return Ledger(tmp_path / "receipts.jsonl")


def test_loop_red_red_green_series(ledger):
    driver = DemoDriver(OPS)
    planner = ScriptedPlanner([{"command": "pytest -q"}] * 5)
    series = run_loop(driver, ledger, planner, task="t", max_iter=5)
    assert [r.run_seq for r in series] == [1, 2, 3]
    assert series[-1].exit_code == 0
    # every run, including failures, is on the ledger
    assert [r.run_seq for r in ledger.by_task("t")] == [1, 2, 3]


def test_loop_stops_at_first_green(ledger):
    ops = [OPS[0], OPS[2]]  # fail then green
    planner = ScriptedPlanner([{"command": "pytest -q"}] * 5)
    series = run_loop(DemoDriver(ops), ledger, planner, task="t", max_iter=5)
    assert len(series) == 2
    assert len(ledger.by_task("t")) == 2


def test_give_up_marks_last_receipt_unresolved(ledger):
    planner = ScriptedPlanner([{"command": "pytest -q"}] * 5)
    # all failing ops -> hits max_iter
    series = run_loop(DemoDriver([OPS[0]] * 5), ledger, planner, task="t", max_iter=3)
    assert len(series) == 3
    last = ledger.get(series[-1].receipt_id)
    assert last.unresolved is True
    assert all(not r.unresolved for r in ledger.by_task("t")[:-1])


def test_recon_exit0_does_not_end_series(ledger):
    """Live-bench regression (2026-09-30): `ls -la` exits 0 without doing any
    work — a bare green exit must not be treated as task completion. Only
    the planner's done ends the series."""
    green_recon = {**OPS[0], "command": "ls -la",
                   "exit_code": 0, "status": "SUCCESS"}
    failing = OPS[0]
    driver = DemoDriver([green_recon, failing])
    planner = ScriptedPlanner([{"command": "ls -la"},
                               {"command": "pytest -q"}])  # then done (None)
    series = run_loop(driver, ledger, planner, task="t", max_iter=5)
    assert len(series) == 2                     # kept going after the green ls
    assert series[-1].exit_code == 1            # ended on the red pytest run
    assert ledger.get(series[-1].receipt_id).unresolved is True


def test_green_final_run_is_not_unresolved(ledger):
    """A series whose last run is green is demonstrably successful — it must
    not carry the unresolved marker even if the loop ended by exhaustion."""
    driver = DemoDriver([OPS[0], OPS[2]])  # fail, then green
    planner = ScriptedPlanner([{"command": "pytest -q"}] * 5)
    series = run_loop(driver, ledger, planner, task="t", max_iter=5)
    assert series[-1].exit_code == 0
    assert ledger.get(series[-1].receipt_id).unresolved is False


def test_planner_done_stops_loop(ledger):
    planner = ScriptedPlanner([{"command": "pytest -q"}])  # then returns None
    series = run_loop(DemoDriver([OPS[0]] * 5), ledger, planner, task="t", max_iter=5)
    assert len(series) == 1
    assert ledger.get(series[0].receipt_id).unresolved is True


class ExplodingPlanner:
    def next(self, history, task=None):
        raise RuntimeError("planner API unreachable")


def test_planner_exception_ends_series_unresolved(ledger):
    """An API crash mid-series must not take the whole series down."""
    planner = ScriptedPlanner([{"command": "pytest -q"}])
    series = run_loop(DemoDriver([OPS[0], OPS[2]]), ledger, planner,
                      task="t", max_iter=5)
    assert len(series) == 1
    planner2 = ExplodingPlanner()
    series = run_loop(DemoDriver(OPS), ledger, planner2, task="t2", max_iter=5)
    assert series == []  # crashed before any run — nothing to mark


def test_planner_exception_marks_last_receipt(ledger):
    class BoomPlanner:
        def __init__(self):
            self.calls = 0
        def next(self, history, task=None):
            self.calls += 1
            if self.calls == 1:
                return {"command": "pytest -q"}
            raise RuntimeError("api dead")

    series = run_loop(DemoDriver(OPS), ledger, BoomPlanner(), task="t", max_iter=5)
    assert len(series) == 1
    assert ledger.get(series[-1].receipt_id).unresolved is True


def test_empty_command_ends_series_unresolved(ledger):
    """Planner emitting an empty command -> DriverError -> series ends clean."""
    planner = ScriptedPlanner([{"command": "pytest -q"}, {"command": "  "},
                               {"command": "pytest -q"}])
    series = run_loop(DemoDriver(OPS), ledger, planner, task="t", max_iter=5)
    assert len(series) == 1
    assert ledger.get(series[-1].receipt_id).unresolved is True


class TestNemotronPlanner:
    """Planner calls the Token Factory chat API; http_post is injected for tests."""

    def make_planner(self, payload):
        calls = []

        def fake_post(url, headers, body):
            calls.append(body)
            return payload

        return NemotronPlanner(api_key="k", model="m", http_post=fake_post), calls

    def test_parses_command_action(self):
        payload = {"choices": [{"message": {"content": '{"command": "pytest -q"}'}}]}
        p, _ = self.make_planner(payload)
        assert p.next([]) == {"command": "pytest -q"}

    def test_parses_done(self):
        payload = {"choices": [{"message": {"content": '{"done": true}'}}]}
        p, _ = self.make_planner(payload)
        assert p.next([]) is None

    def test_reasoning_preface_is_skipped(self):
        """Reasoning models emit prose before the final JSON — extract the last object."""
        payload = {"choices": [{"message": {"content": 'thinking about it...\n{"command": "make test"}'}}]}
        p, _ = self.make_planner(payload)
        assert p.next([]) == {"command": "make test"}

    def test_garbage_response_returns_none(self):
        payload = {"choices": [{"message": {"content": "no json here"}}]}
        p, _ = self.make_planner(payload)
        assert p.next([]) is None

    def test_task_reaches_the_model(self):
        """P0: the planner must know the task — a bench run without it
        measures nothing."""
        payload = {"choices": [{"message": {"content": '{"command": "x"}'}}]}
        p, calls = self.make_planner(payload)
        p.next([], task="fix median()")
        assert "fix median()" in calls[0]["messages"][1]["content"]
