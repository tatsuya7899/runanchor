"""Acceptance scenarios S1/S3/S4: receipt issuance + append-only ledger + state machine."""

import json

import pytest

from runanchor.ledger import DuplicateReceipt, InvalidTransition, Ledger
from runanchor.receipt import OperationRecord, fingerprint, issue_receipt


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


def _receipt_lines(ledger):
    return [json.loads(l)["receipt"]
            for l in ledger.path.read_text().strip().splitlines()]


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

    def test_receipt_carries_evidence_fields(self):
        """S2: the display fields exist and are populated."""
        r = issue_receipt(make_op(), task="t", run_seq=1)
        assert r.diff_sha256 == "a" * 64
        assert r.duration_s == 1.2
        assert r.consumed_cpu_s == 0.8
        assert r.consumed_memory == 262144
        assert r.consumed_memory_unit == "bytes"
        assert r.stdout_tail and r.issued_at

    def test_ids_differ_between_runs(self):
        a = issue_receipt(make_op(), task="t", run_seq=1)
        b = issue_receipt(make_op(), task="t", run_seq=2)
        assert a.receipt_id != b.receipt_id

    def test_stdout_is_fingerprinted_and_trimmed(self):
        r = issue_receipt(make_op(stdout="x\n" * 500), task="t", run_seq=1)
        assert len(r.stdout_sha256) == 64
        assert len(r.stdout_tail.splitlines()) <= 20

    def test_timing_jitter_normalizes_to_same_fingerprint(self):
        a = issue_receipt(make_op(stdout="1 passed in 0.42s\n"), task="t", run_seq=1)
        b = issue_receipt(make_op(stdout="1 passed in 0.19s\n"), task="t", run_seq=2)
        assert a.stdout_sha256 == b.stdout_sha256 == fingerprint("1 passed in 0.42s\n")

    def test_failed_run_still_gets_receipt(self):
        """FR-1: failed attempts are receipts too, not discarded."""
        r = issue_receipt(make_op(status="FAILED", exit_code=1), task="t", run_seq=1)
        assert r.status == "FAILED"
        assert r.exit_code == 1
        assert r.state == "pending"

    def test_driver_error_run_still_gets_receipt(self):
        """FR-1: even an execution that produced no provider record lands."""
        r = issue_receipt(make_op(operation_uuid=None, status="DRIVER_ERROR",
                                  exit_code=None), task="t", run_seq=1)
        assert r.status == "DRIVER_ERROR"
        assert r.operation_uuid is None

    def test_demo_receipt_is_marked(self):
        """FR-6: demo receipts must not pretend to be live runs."""
        r = issue_receipt(make_op(demo=True), task="t", run_seq=1)
        assert r.demo is True

    def test_secrets_are_scrubbed_before_persistence(self):
        """The ledger may be published with the measurement package (FR-11) —
        secret-shaped strings must never reach it."""
        r = issue_receipt(
            make_op(command="deploy --token sk-abc123def456ghi789",
                    stdout="key: Bearer aaa.bbb.ccc\nok\n"),
            task="t", run_seq=1)
        blob = json.dumps(r.to_dict())
        assert "sk-abc123def456ghi789" not in blob
        assert "aaa.bbb.ccc" not in blob
        assert "REDACTED" in blob

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
        rows = _receipt_lines(ledger)
        assert len(rows) == 1
        assert rows[0]["receipt_id"] == r.receipt_id

    def test_append_rejects_non_pending(self, ledger):
        from dataclasses import replace
        r = replace(issue_receipt(make_op(), task="t", run_seq=1), state="adopted")
        with pytest.raises(ValueError):
            ledger.append_receipt(r)

    def test_append_rejects_duplicate_id(self, ledger):
        r = issue_receipt(make_op(), task="t", run_seq=1)
        ledger.append_receipt(r)
        with pytest.raises(DuplicateReceipt):
            ledger.append_receipt(r)

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

    def test_mismatch_can_be_overridden_by_human(self, ledger):
        """mismatch is evidence, not a terminal verdict — a human may still decide."""
        r = issue_receipt(make_op(), task="t", run_seq=1)
        ledger.append_receipt(r)
        ledger.decide(r.receipt_id, "mismatch", by="verifier", reason="replay differs")
        updated = ledger.decide(r.receipt_id, "rejected", by="human",
                                reason="confirmed fabrication")
        assert updated.state == "rejected"

    def test_history_preserves_all_snapshots(self, ledger):
        r = issue_receipt(make_op(), task="t", run_seq=1)
        ledger.append_receipt(r)
        ledger.decide(r.receipt_id, "adopted", by="human")
        hist = ledger.history(r.receipt_id)
        assert [h.state for h in hist] == ["pending", "adopted"]

    def test_decide_unknown_receipt(self, ledger):
        with pytest.raises(KeyError):
            ledger.decide("nope", "adopted", by="human")


class TestIntegrity:
    def test_chain_detects_tampering(self, tmp_path):
        path = tmp_path / "receipts.jsonl"
        ledger = Ledger(path)
        for i in range(3):
            ledger.append_receipt(issue_receipt(make_op(), task="t", run_seq=i + 1))
        assert ledger.check_integrity() == []
        # forge: rewrite middle line's state
        lines = path.read_text().splitlines()
        row = json.loads(lines[1])
        row["receipt"]["state"] = "adopted"
        lines[1] = json.dumps(row)
        path.write_text("\n".join(lines) + "\n")
        broken = ledger.check_integrity()
        # tampering line 2 invalidates line 3's chain link — the forgery is
        # detected at the successor's position
        assert broken == [3]

    def test_corrupt_tail_line_does_not_kill_ledger(self, tmp_path):
        path = tmp_path / "receipts.jsonl"
        ledger = Ledger(path)
        ledger.append_receipt(issue_receipt(make_op(), task="t", run_seq=1))
        with path.open("a") as f:
            f.write('{"_chain": "x", "receipt": {"receip')  # torn write
        assert len(ledger.all()) == 1          # good rows still readable
        assert ledger.corrupt_lines() == [2]   # and the damage is visible
