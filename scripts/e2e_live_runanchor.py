#!/usr/bin/env python3
"""Live end-to-end smoke test: real ConTree run -> receipt -> verify.

Usage:  python3 scripts/e2e_live_runanchor.py

Requires: contree CLI with Sandboxes beta access (NEBIUS_API_KEY configured).
Creates two throwaway sessions (work + verify), issues a receipt for a
deterministic run, replays it through the real verifier, then deletes both
sessions. Exits 0 on verdict=match, 1 otherwise.
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from runanchor.contree_driver import ContreeDriver, DriverError  # noqa: E402
from runanchor.receipt import issue_receipt                     # noqa: E402
from runanchor.verifier import verify_receipt                   # noqa: E402

STAMP = int(time.time())
WORK_SESSION = f"ra_e2e_{STAMP}"
VERIFY_SESSION = f"ra_e2e_verify_{STAMP}"


def main() -> int:
    work = ContreeDriver(session=WORK_SESSION)
    try:
        work.use("tag:python:3.12-slim")
        print(f"bound image: {work.current_image}")
        op = work.run("echo runanchor-e2e", cwd="/work")
    except DriverError as e:
        print(f"setup failed: {e}")
        return 1
    finally:
        work.close()

    receipt = issue_receipt(op, task="e2e smoke", run_seq=1)
    print(f"receipt {receipt.receipt_id[:8]}  op={op.operation_uuid}")
    print(f"  image_uuid={op.image_uuid}  result_image_uuid={op.result_image_uuid}")
    print(f"  exit_code={op.exit_code}  stdout={op.stdout!r}  anchor={op.anchor_source}")
    if op.parse_warnings:
        print(f"  warnings={op.parse_warnings}")

    verify = ContreeDriver(session=VERIFY_SESSION)
    result = verify_receipt(receipt, verify)
    print(f"verify: {result.verdict}")
    for name, diff in result.diffs.items():
        print(f"  {name}: expected={json.dumps(diff['expected'])} "
              f"actual={json.dumps(diff['actual'])}")
    if result.replay_operation_uuid:
        print(f"  replay op: {result.replay_operation_uuid} "
              f"(anchor={result.replay_anchor_source})")
    return 0 if result.verdict == "match" else 1


if __name__ == "__main__":
    sys.exit(main())
