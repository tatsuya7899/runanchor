"""Acceptance S2/S3/S4/S7 at the CLI level: list/show/approve/reject/demo."""

import json
from pathlib import Path

import pytest

from runanchor.cli import main
from runanchor.ledger import Ledger
from runanchor.receipt import OperationRecord, issue_receipt


def op(uuid="op-1"):
    return OperationRecord(
        operation_uuid=uuid, image_uuid="img-a", result_image_uuid="img-b",
        command="pytest -q", cwd="/work", shell_mode=False, status="SUCCESS",
        exit_code=0, stdout="1 passed\n", stderr="",
    )


@pytest.fixture
def ledger_path(tmp_path):
    p = tmp_path / "state" / "receipts.jsonl"
    ledger = Ledger(p)
    for i in range(2):
        ledger.append_receipt(issue_receipt(op(f"op-{i}"), task="t", run_seq=i + 1))
    return p


def test_list_shows_pending_receipts(ledger_path, capsys):
    assert main(["--ledger", str(ledger_path), "list"]) == 0
    out = capsys.readouterr().out
    assert "pending" in out
    assert "t" in out


def test_show_displays_receipt_fields(ledger_path, capsys):
    """S2: show displays the evidence fields."""
    rid = Ledger(ledger_path).all()[0].receipt_id
    assert main(["--ledger", str(ledger_path), "show", rid[:8]]) == 0  # prefix ok
    out = capsys.readouterr().out
    for needle in ("pytest -q", "op-0", "exit", "issued_at"):
        assert needle in out


def test_approve_via_cli(ledger_path, capsys):
    rid = Ledger(ledger_path).all()[0].receipt_id
    assert main(["--ledger", str(ledger_path), "approve", rid]) == 0
    assert Ledger(ledger_path).get(rid).state == "adopted"


def test_reject_via_cli_requires_reason(ledger_path, capsys):
    rid = Ledger(ledger_path).all()[0].receipt_id
    rc = main(["--ledger", str(ledger_path), "reject", rid, "--reason", ""])
    assert rc != 0
    assert Ledger(ledger_path).get(rid).state == "pending"


def test_reject_via_cli_records_reason(ledger_path):
    rid = Ledger(ledger_path).all()[0].receipt_id
    assert main(["--ledger", str(ledger_path), "reject", rid, "--reason", "stale log"]) == 0
    assert Ledger(ledger_path).get(rid).decision["reason"] == "stale log"


def test_demo_runs_offline(tmp_path, capsys, monkeypatch):
    """S7: demo mode needs no credentials and never reaches the network."""
    for var in ("NEBIUS_API_KEY", "CONTREE_TOKEN"):
        monkeypatch.delenv(var, raising=False)
    rc = main(["--ledger", str(tmp_path / "demo.jsonl"), "demo"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "DEMO" in out
    assert "adopted" in out or "rejected" in out


def test_verify_demo_receipt(tmp_path, capsys):
    """verify against the demo fixture driver -> match (S5 demo path)."""
    ledger_path = tmp_path / "demo.jsonl"
    assert main(["--ledger", str(ledger_path), "demo"]) == 0
    capsys.readouterr()
    ledger = Ledger(ledger_path)
    green = [r for r in ledger.all() if r.exit_code == 0][0]
    assert main(["--ledger", str(ledger_path), "verify", green.receipt_id, "--driver", "demo"]) == 0
    out = capsys.readouterr().out
    assert "match" in out


def test_run_without_credentials_fails_cleanly(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    # isolate HOME so the contree auth.ini fallback can't find credentials —
    # the test must not depend on whether this machine has `contree auth` done
    monkeypatch.setenv("HOME", str(tmp_path))
    rc = main(["--ledger", str(tmp_path / "l.jsonl"), "run", "fix the bug"])
    assert rc != 0
    assert "NEBIUS_API_KEY" in capsys.readouterr().out


def test_check_reports_intact_ledger(ledger_path, capsys):
    assert main(["--ledger", str(ledger_path), "check"]) == 0
    out = capsys.readouterr().out
    assert "hash chain intact" in out
    assert "snapshots" in out and "receipts" in out


def test_check_detects_tampered_ledger(ledger_path, capsys):
    """Flip a byte in a middle line — the chain check must flag it."""
    lines = ledger_path.read_text().splitlines()
    mid = json.loads(lines[0])
    mid["receipt"]["command"] = "rm -rf /"  # tamper with recorded evidence
    lines[0] = json.dumps(mid)
    ledger_path.write_text("\n".join(lines) + "\n")
    assert main(["--ledger", str(ledger_path), "check"]) == 1
    assert "CHAIN BROKEN" in capsys.readouterr().out


def test_check_accepts_ledger_after_subcommand(ledger_path, capsys):
    """`runanchor check --ledger <file>` must parse — the flag lives both
    globally and on the subcommand."""
    assert main(["check", "--ledger", str(ledger_path)]) == 0
    assert "hash chain intact" in capsys.readouterr().out


def test_check_missing_ledger_fails_closed(tmp_path, capsys):
    """A nonexistent ledger must NOT report '0 receipts, chain intact' —
    that would be a false-green audit."""
    rc = main(["--ledger", str(tmp_path / "nope.jsonl"), "check"])
    assert rc == 1
    assert "not found" in capsys.readouterr().out


def test_verify_scrubbed_receipt_is_unverifiable_exit3(tmp_path, capsys):
    """A receipt whose recorded command was secret-scrubbed cannot be
    replayed faithfully — verify exits 3 (unverifiable), distinct from
    mismatch=1 and match=0."""
    ledger_path = tmp_path / "l.jsonl"
    ledger = Ledger(ledger_path)
    r = issue_receipt(op(), task="t", run_seq=1)
    ledger.append_receipt(r)
    # forge a receipt whose command already carries the REDACTED marker by
    # re-issuing with a secret-shaped command (issue_receipt scrubs it)
    from runanchor.receipt import OperationRecord as Op
    op2 = Op(operation_uuid="op-9", image_uuid="img-a",
             result_image_uuid="img-b",
             command="curl -H 'Bearer aaabbbcccdddeeefff' x", cwd="/work",
             shell_mode=False, status="SUCCESS", exit_code=0,
             stdout="ok\n", stderr="")
    r2 = issue_receipt(op2, task="t", run_seq=2)
    ledger.append_receipt(r2)
    rc = main(["--ledger", str(ledger_path), "verify", r2.receipt_id,
               "--driver", "demo"])
    out = capsys.readouterr().out
    assert rc == 3
    assert "unverifiable" in out
