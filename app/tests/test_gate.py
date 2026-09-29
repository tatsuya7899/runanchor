"""Acceptance S3/S4 at the gate API level: pending list, approve, reject."""

import pytest

from runanchor.gate import Gate
from runanchor.ledger import Ledger
from runanchor.receipt import OperationRecord, issue_receipt


def op(uuid="op-1"):
    return OperationRecord(
        operation_uuid=uuid,
        image_uuid="img-a",
        result_image_uuid="img-b",
        command="pytest -q",
        cwd="/work",
        shell_mode=False,
        status="SUCCESS",
        exit_code=0,
        stdout="ok\n",
        stderr="",
    )


@pytest.fixture
def gate(tmp_path):
    ledger = Ledger(tmp_path / "receipts.jsonl")
    for i in range(2):
        ledger.append_receipt(issue_receipt(op(f"op-{i}"), task="t", run_seq=i + 1))
    return Gate(ledger)


def test_pending_lists_only_undecided(gate):
    pending = gate.pending()
    assert len(pending) == 2
    gate.approve(pending[0].receipt_id, by="human")
    assert [r.receipt_id for r in gate.pending()] == [pending[1].receipt_id]


def test_approve_marks_adopted(gate):
    r = gate.pending()[0]
    gate.approve(r.receipt_id, by="human")
    assert gate.ledger.get(r.receipt_id).state == "adopted"


def test_reject_requires_reason(gate):
    r = gate.pending()[0]
    with pytest.raises(ValueError):
        gate.reject(r.receipt_id, by="human", reason="")
    assert gate.ledger.get(r.receipt_id).state == "pending"


def test_reject_keeps_receipt(gate):
    r = gate.pending()[0]
    gate.reject(r.receipt_id, by="human", reason="test log looks fabricated")
    kept = gate.ledger.get(r.receipt_id)
    assert kept.state == "rejected"
    assert kept.decision["reason"] == "test log looks fabricated"


def test_decide_by_judge_records_actor(gate):
    r = gate.pending()[0]
    gate.approve(r.receipt_id, by="judge:nemotron-lightning")
    assert gate.ledger.get(r.receipt_id).decision["by"] == "judge:nemotron-lightning"
