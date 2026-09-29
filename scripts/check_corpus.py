#!/usr/bin/env python3
"""Mechanical corpus sanity check: run pytest inside every seed/ workspace
and report the observed result vs the declared label/oracle expectation.

- clean items: tests SHOULD start red (they are bug-fix tasks)
- seeded items: SHOULD start red too, or have a deceptive wrapper — the point
  is the trap, not the start state; we report what we observe
- items with non-.py seeds (shim scripts) get their notes printed

Not a gate — a report. Run: python3 scripts/check_corpus.py
"""

import subprocess
import sys
import tempfile
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "app" / "corpus"


def main() -> int:
    rows = []
    for d in sorted(CORPUS.iterdir()):
        if not d.is_dir() or not (d / "label.json").exists():
            continue
        import json
        label = json.loads((d / "label.json").read_text())
        # copy seed to tmp so agent-side artifacts never pollute the repo
        with tempfile.TemporaryDirectory() as td:
            shutil.copytree(d / "seed", td, dirs_exist_ok=True)
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", "--tb=no", "-p", "no:cacheprovider"],
                cwd=td, capture_output=True, text=True, timeout=60)
            summary = (proc.stdout.strip().splitlines() or ["<no output>"])[-1]
        rows.append((d.name, label["label"], proc.returncode, summary))

    for name, lbl, rc, summary in rows:
        state = "green" if rc == 0 else f"red(rc={rc})"
        print(f"{name:<32} {lbl:<6} {state:<10} {summary[:72]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
