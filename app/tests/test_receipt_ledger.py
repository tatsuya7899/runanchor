"""Acceptance scenarios S1/S3/S4: receipt issuance + append-only ledger + state machine."""

import json

import pytest

from runanchor.ledger import InvalidTransition, Ledger
from runanchor.receipt import OperationRecord, issue_receipt


def make_op(**overrides):
    fields = dict(
        operation_uuid="op-uuid-0001",
        image_uuid="img-start",
        result_image_uuid="img-end",
        command="pytest -q",
        cwd="/work",
        shell_mode=False,
        status="SUCCESS",
        exit_code=0,
        stdout="collected 1 item\n1 passed in 0.02s\n",
        stderr="",
        diff_sha256="a" * 64,
        duration_s=1.2,
        consumed_cpu_s=0.8,
        consumed_memory=262144,
        consumed_memory_unit="bytes",
    )
    fields.update(overrides)
    return OperationRecord(**fields)


@pytest.fixture
def ledger(tmp_path):
    return Ledger(tmp_path / "state" / "receipts.jsonl")


class TestIssuance:
    """S1: each run produces a unique receipt anchored to the provider record."""

    def test_receipt_has_unique_id_and_provider_ref(self):
        r = issue_receipt(make_op(), task="fix-sort", run_seq=1, model="nemotron")
        assert r.receipt_id
        assert r.operation_uuid == "op-uuid-0001"
        assert r.image_uuid == "img-start"
        assert r.result_image_uuid == "img-end"
        assert r.state == "pending"
        assert r.demo is False

    def test_ids_differ_between_runs(self):
        a = issue_receipt(make_op(), task="t", run_seq=1)
        b = issue_receipt(make_op(), task="t", run_seq=2)
        assert a.receipt_id != b.receipt_id

    def test_stdout_is_fingerprinted_and_trimmed(self):
        r = issue_receipt(make_op(stdout="x\n" * 500), task="t", run_seq=1)
        assert len(r.stdout_sha256) == 64
        assert len(r.stdout_tail.splitlines()) <= 20

    def test_failed_run_still_gets_receipt(self):
        """FR-1: failed attempts are receipts too, not discarded."""
        r = issue_receipt(make_op(status="FAILURE", exit_code=1), task="t", run_seq=1)
        assert r.status == "FAILURE"
        assert r.exit_code == 1
        assert r.state == "pending"

    def test_demo_receipt_is_marked(self):
        """FR-6: demo receipts must not pretend to be live runs."""
        r = issue_receipt(make_op(operation_uuid=None), task="t", run_seq=1, demo=True)
        assert r.demo is True

    def test_seed_carries_non_determinism_note(self):
        r = issue_receipt(make_op(), task="t", run_seq=1, seed=42)
        assert r.seed == 42
        assert r.seed_note is not None


class TestLedger:
    def test_append_and_reload(self, ledger):
        r = issue_receipt(make_op(), task="t", run_seq=1)
        ledger.append_receipt(r)
        loaded = ledger.get(r.receipt_id)
        assert loaded.receipt_id == r.receipt_id
        assert loaded.state == "pending"
        lines = ledger.path.read_text().strip().splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["receipt_id"] == r.receipt_id

    def test_task_series_reconstructed(self, ledger):
        for seq in (1, 2, 3):
            ledger.append_receipt(issue_receipt(make_op(), task="t", run_seq=seq))
        ledger.append_receipt(issue_receipt(make_op(), task="other", run_seq=1))
        series = [r.run_seq for r in ledger.by_task("t")]
        assert series == [1, 2, 3]

    """S3: approve a pending receipt -> adopted in the ledger."""

    def test_approve_pending(self, ledger):
        r = issue_receipt(make_op(), task="t", run_seq=1)
        ledger.append_receipt(r)
        updated = ledger.decide(r.receipt_id, "adopted", by="human")
        assert updated.state == "adopted"
        assert updated.decision["by"] == "human"
        assert ledger.get(r.receipt_id).state == "adopted"
        assert ledger.pending() == []

    """S4: reject requires a reason and the receipt is never deleted."""

    def test_reject_requires_reason(self, ledger):
        r = issue_receipt(make_op(), task="t", run_seq=1)
        ledger.append_receipt(r)
        for bad in (None, "", "   "):
            with pytest.raises(ValueError):
                ledger.decide(r.receipt_id, "rejected", by="human", reason=bad)
        assert ledger.get(r.receipt_id).state == "pending"

    def test_rejected_receipt_is_retained(self, ledger):
        r = issue_receipt(make_op(), task="t", run_seq=1)
        ledger.append_receipt(r)
        ledger.decide(r.receipt_id, "rejected", by="human", reason="did not run tests")
        kept = ledger.get(r.receipt_id)
        assert kept.state == "rejected"
        assert kept.decision["reason"] == "did not run tests"
        # append-only: the file grew, nothing was removed
        assert len(ledger.path.read_text().strip().splitlines()) == 2

    def test_non_pending_cannot_be_decided(self, ledger):
        r = issue_receipt(make_op(), task="t", run_seq=1)
        ledger.append_receipt(r)
        ledger.decide(r.receipt_id, "adopted", by="human")
        with pytest.raises(InvalidTransition):
            ledger.decide(r.receipt_id, "rejected", by="human", reason="x")

    def test_adopted_can_be_marked_mismatch(self, ledger):
        """Post-approval verify may find a replay mismatch."""
        r = issue_receipt(make_op(), task="t", run_seq=1)
        ledger.append_receipt(r)
        ledger.decide(r.receipt_id, "adopted", by="human")
        updated = ledger.decide(r.receipt_id, "mismatch", by="verifier", reason="replay differs")
        assert updated.state == "mismatch"

    def test_decide_unknown_receipt(self, ledger):
        with pytest.raises(KeyError):
            ledger.decide("nope", "adopted", by="human")
