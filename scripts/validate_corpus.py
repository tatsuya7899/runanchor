#!/usr/bin/env python3
"""Validate the corpus oracles: run each item's hidden oracle against the
raw SEED state locally and report outcomes.

Expectations encoded per item:
- seeded items: the oracle SHOULD fail against the unmodified seed (the trap
  is still present). A seeded item whose oracle passes on seed state means
  the trap isn't actually probed — a corpus defect.
- clean items: the oracle MAY pass or fail on seed state (a clean task can
  still carry an honest failing test the agent must fix); the report flags
  collection errors only.

Usage: python3 scripts/validate_corpus.py [--corpus app/corpus]
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_oracle(item_dir: Path, tmp: Path) -> tuple[int, str]:
    shutil.copytree(item_dir / "seed", tmp, dirs_exist_ok=True)
    oracle_dst = tmp / "oracle"
    shutil.copytree(item_dir / "oracle", oracle_dst, dirs_exist_ok=True)
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "oracle/"],
        cwd=tmp, capture_output=True, text=True, timeout=120,
    )
    tail = (proc.stdout + proc.stderr).strip().splitlines()
    return proc.returncode, (tail[-1] if tail else "")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(ROOT / "app" / "corpus"))
    args = ap.parse_args()
    corpus = Path(args.corpus)

    problems = []
    rows = []
    for item in sorted(p for p in corpus.iterdir() if p.is_dir()):
        meta = json.loads((item / "label.json").read_text())
        has_oracle = (item / "oracle").is_dir()
        if not has_oracle:
            problems.append(f"{item.name}: missing oracle/")
            continue
        with tempfile.TemporaryDirectory() as td:
            try:
                rc, tail = run_oracle(item, Path(td))
            except subprocess.TimeoutExpired:
                problems.append(f"{item.name}: oracle timed out on seed state")
                continue
        collected = "no tests ran" in tail or "error" in tail.lower() and rc == 4
        rows.append((item.name, meta["label"], rc, tail))
        if rc == 4 or "no tests ran" in tail:
            problems.append(f"{item.name}: oracle collected nothing ({tail})")
        elif meta["label"] == "seeded" and rc == 0:
            problems.append(
                f"{item.name}: seeded item but oracle PASSES on raw seed — "
                f"the trap is not actually probed")
        elif collected:
            problems.append(f"{item.name}: collection error ({tail})")

    for slug, label, rc, tail in rows:
        print(f"  {slug:<32} {label:<6} seed-oracle exit={rc}  {tail[:70]}")
    print()
    if problems:
        print("PROBLEMS:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"ok: {len(rows)} items, oracles valid against seed state")
    return 0


if __name__ == "__main__":
    sys.exit(main())
