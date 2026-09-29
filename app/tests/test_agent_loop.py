"""Acceptance S9: the autonomous loop issues one receipt per run, in series."""

import json

import pytest

from runanchor.agent_loop import NemotronPlanner, ScriptedPlanner, run_loop
from runanchor.contree_driver import DemoDriver
from runanchor.ledger import Ledger
from runanchor.receipt import issue_receipt

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


def test_planner_done_stops_loop(ledger):
    planner = ScriptedPlanner([{"command": "pytest -q"}])  # then returns None
    series = run_loop(DemoDriver([OPS[0]] * 5), ledger, planner, task="t", max_iter=5)
    assert len(series) == 1
    assert ledger.get(series[0].receipt_id).unresolved is True


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
