"""Demo mode: the whole product flow, offline, on recorded fixtures.

Scripted narrative: an agent attempts a task (red -> red -> green), each run
gets a receipt marked demo=True, the green run is replay-verified, then the
gate rejects a false-claim run and adopts the verified one. Nothing leaves
the machine — the demo driver never touches the network.
"""

from __future__ import annotations

from pathlib import Path

from .contree_driver import DemoDriver
from .gate import Gate
from .ledger import Ledger
from .receipt import issue_receipt
from .verifier import DEFAULT_ORACLE_COMMAND, verify_receipt

DEMO_TASK = "demo-fix-sort"


def run_demo(fixture_dir, ledger_path) -> dict:
    fixture_dir = Path(fixture_dir)
    run_driver = DemoDriver.from_dir(fixture_dir)
    verify_driver = DemoDriver.from_dir(fixture_dir / "verify")
    ledger = Ledger(ledger_path)
    gate = Gate(ledger)

    lines: list[str] = []
    receipts = []

    run_driver.use("demo:base-image")
    lines.append("[DEMO] image selected: demo:base-image")

    seq = 0
    while run_driver.remaining:
        seq += 1
        op = run_driver.run("pytest -q", cwd="/work")
        r = issue_receipt(op, task=DEMO_TASK, run_seq=seq, model="demo", demo=True)
        ledger.append_receipt(r)
        receipts.append(r)
        lines.append(
            f"[DEMO] run {seq}: status={r.status} exit={r.exit_code} "
            f"receipt={r.receipt_id[:8]} (op={r.operation_uuid})"
        )

    final = receipts[-1]
    result = verify_receipt(
        final, verify_driver,
        # hidden-oracle stage: the fixture's second op plays the oracle run —
        # a suite the demo "agent" never saw, executed on the result image
        oracle_command=DEFAULT_ORACLE_COMMAND,
    )
    lines.append(f"[DEMO] verify {final.receipt_id[:8]}: {result.verdict}")
    if result.oracle is not None:
        lines.append(
            f"[DEMO] hidden oracle on result image: {result.oracle['verdict']} "
            f"(op={result.oracle_operation_uuid})")

    gate.reject(
        receipts[1].receipt_id,
        by="human",
        reason="agent claimed success but the recorded test log shows a failure",
    )
    lines.append(f"[DEMO] rejected {receipts[1].receipt_id[:8]} (false success claim)")

    gate.approve(final.receipt_id, by="human", reason="replay verified")
    lines.append(f"[DEMO] adopted {final.receipt_id[:8]}")

    states = [r.state for r in ledger.all()]
    return {
        "receipts_issued": len(receipts),
        "verifications": [
            {"receipt_id": result.receipt_id, "verdict": result.verdict, "diffs": result.diffs}
        ],
        "decisions": {"adopted": states.count("adopted"), "rejected": states.count("rejected")},
        "lines": lines,
    }
