#!/usr/bin/env python3
"""Record the runanchor demo as a capture-ready terminal session.

Prints the demo flow with deliberate pacing (typewriter-ish delays) so a
screen recording picks up each beat. Read the narration cues from
submit/demo-script.md — this script produces the visual track.

Usage:
    python3 scripts/record_demo.py            # paced for capture
    python3 scripts/record_demo.py --fast     # no pacing (dry run)
"""

import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
FAST = "--fast" in sys.argv


def beat(seconds: float) -> None:
    if not FAST:
        time.sleep(seconds)


def run(cmd: list[str], cwd=None) -> None:
    print(f"\n$ {' '.join(cmd)}", flush=True)
    beat(0.8)
    proc = subprocess.run(cmd, cwd=cwd or APP)
    beat(1.4)


def main() -> int:
    td = tempfile.mkdtemp(prefix="runanchor-demo-")
    ledger = Path(td) / "demo.jsonl"
    cli = [sys.executable, "-m", "runanchor.cli", "--ledger", str(ledger)]

    print("# runanchor demo — every agent run gets a verifiable receipt", flush=True)
    beat(2.0)

    run(cli + ["demo"])
    beat(2.0)

    run(cli + ["list"])

    print("\n# inspect the adopted receipt (provider-anchored evidence)", flush=True)
    beat(1.5)
    out = subprocess.run(cli + ["list"], cwd=APP,
                         capture_output=True, text=True).stdout
    adopted_id = None
    for line in out.splitlines():
        if "state=adopted" in line:
            adopted_id = line.split()[0]
    if adopted_id:
        run(cli + ["show", adopted_id])
    else:
        print("(no adopted receipt found — demo output changed?)")

    print("\n# receipts live on an append-only, hash-chained ledger", flush=True)
    print("# rejected and failed runs stay recorded — evidence is never deleted", flush=True)
    beat(2.5)

    print(f"\n# ledger kept at {ledger} (temp dir for the recording)", flush=True)
    shutil.rmtree(td, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
