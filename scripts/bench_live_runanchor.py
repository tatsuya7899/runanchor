#!/usr/bin/env python3
"""Live corpus benchmark: labeled corpus -> real ConTree runs -> replay+oracle
verification -> Nemotron judge (two layers: evidence-only and full gate).

Usage:  python3 scripts/bench_live_runanchor.py [--out eval/bench-YYYYMMDD.json]

Requires: contree CLI with Sandboxes beta access. Credentials come from
NEBIUS_API_KEY or the `contree auth` profile token (~/.config/contree/auth.ini).
Runs the `runanchor-bench` image (eval/runanchor-bench-image/Dockerfile;
rebuild with `contree build --tag runanchor-bench eval/runanchor-bench-image`).
Each corpus item runs in a throwaway session (work + verify), both deleted
afterwards.
"""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from runanchor.agent_loop import NemotronPlanner                    # noqa: E402
from runanchor.bench import run_bench                               # noqa: E402
from runanchor.cli import _api_key                                  # noqa: E402
from runanchor.contree_driver import ContreeDriver                  # noqa: E402
from runanchor.judge import NemotronJudge                           # noqa: E402
from runanchor.ledger import Ledger                                 # noqa: E402

CORPUS = Path(__file__).resolve().parent.parent / "app" / "corpus"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(CORPUS))
    ap.add_argument("--image", default="runanchor-bench")
    ap.add_argument("--session", default="runanchor-bench")
    ap.add_argument("--model", default="nvidia/Nemotron-3_5-Lightning")
    ap.add_argument("--planner-model", default=None,
                    help="defaults to --model; the planner drives the agent loop")
    ap.add_argument("--judge-model", default=None,
                    help="defaults to --model; the judge reviews evidence")
    ap.add_argument("--max-iter", type=int, default=8)
    ap.add_argument("--no-verify", action="store_true",
                    help="skip replay+oracle (evidence-only baseline)")
    ap.add_argument("--ledger", required=True,
                    help="ledger path for this run (required — never append to "
                         "a published ledger artifact)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--only", default=None, metavar="SLUG[,SLUG...]",
                    help="run only these corpus items (comma-separated) — "
                         "smoke-test path; results are not the benchmark")
    args = ap.parse_args()

    corpus_dir = args.corpus
    if args.only:
        # smoke run: build a filtered corpus view by symlinking the selected
        # items into a temp dir (corpus loader iterates directories)
        import tempfile
        keep = set(args.only.split(","))
        tmp = tempfile.TemporaryDirectory(prefix="runanchor-bench-only-")
        corpus_dir = tmp.name
        missing = keep - {p.name for p in Path(args.corpus).iterdir() if p.is_dir()}
        if missing:
            print(f"error: unknown corpus items: {sorted(missing)}")
            return 2
        for slug in keep:
            src = Path(args.corpus) / slug
            dst = Path(corpus_dir) / slug
            try:
                dst.symlink_to(src.resolve())
            except OSError:
                import shutil
                shutil.copytree(src, dst)

    api_key = _api_key()
    if not api_key:
        print("error: no Token Factory credentials "
              "(NEBIUS_API_KEY or `contree auth` profile token)")
        return 2

    judge = NemotronJudge(api_key=api_key,
                          model=args.judge_model or args.model)
    planner_model = args.planner_model or args.model

    def driver_for(item):
        d = ContreeDriver(session=f"{args.session}-{item.slug}")
        d.use(args.image)
        return d

    def verify_driver_for(item):
        return ContreeDriver(session=f"{args.session}-{item.slug}-verify")

    report = run_bench(
        corpus_dir, Ledger(args.ledger),
        driver_for=driver_for,
        planner_for=lambda item: NemotronPlanner(api_key=api_key,
                                                 model=planner_model),
        judge=judge,
        verify_driver_for=None if args.no_verify else verify_driver_for,
        max_iter=args.max_iter,
    )
    for line in report.lines:
        print(line)
    if args.out:
        Path(args.out).write_text(json.dumps(
            {"matrix": asdict(report.matrix),
             "evidence_matrix": asdict(report.evidence_matrix),
             "truth_source": report.truth_source,
             "rows": report.rows,
             "sensitivity": report.sensitivity,
             "specificity": report.specificity}, indent=2))
        print(f"report written: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
