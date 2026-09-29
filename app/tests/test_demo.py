"""Acceptance S7 core: demo mode runs the full flow offline, receipts marked demo."""

import json
from pathlib import Path

import pytest

from runanchor.demo import run_demo
from runanchor.ledger import Ledger

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "demo"


def test_demo_fixture_exists():
    assert (FIXTURE_DIR / "ops.jsonl").exists()
    assert (FIXTURE_DIR / "verify" / "ops.jsonl").exists()


def test_demo_runs_offline_and_produces_receipts(tmp_path):
    report = run_demo(FIXTURE_DIR, tmp_path / "demo-ledger.jsonl")
    assert report["receipts_issued"] == 3
    assert report["verifications"][0]["verdict"] == "match"
    assert report["decisions"] == {"adopted": 1, "rejected": 1}


def test_all_demo_receipts_are_marked(tmp_path):
    ledger_path = tmp_path / "demo-ledger.jsonl"
    run_demo(FIXTURE_DIR, ledger_path)
    ledger = Ledger(ledger_path)
    receipts = ledger.all()
    assert len(receipts) == 3
    assert all(r.demo for r in receipts)
    assert {r.state for r in receipts} == {"adopted", "rejected", "pending"}


def test_demo_summary_is_printable(tmp_path, capsys):
    report = run_demo(FIXTURE_DIR, tmp_path / "demo-ledger.jsonl")
    assert report["lines"]  # narratable steps
    assert any("DEMO" in line for line in report["lines"])  # FR-6 provenance mark
