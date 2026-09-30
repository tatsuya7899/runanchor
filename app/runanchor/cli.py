"""runanchor CLI: run / list / show / approve / reject / verify / bench / demo.

`demo` runs the full flow on recorded fixtures — no credentials, no network.
`run` is live-only (needs NEBIUS_API_KEY + the contree CLI). `verify` defaults
to the live driver; --driver demo replays the recorded verify fixture.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

from .agent_loop import NemotronPlanner, run_loop
from .contree_driver import ContreeDriver, DemoDriver, DriverError
from .demo import run_demo
from .gate import Gate
from .ledger import InvalidTransition, Ledger
from .verifier import verify_receipt

DEFAULT_LEDGER = Path("state/receipts.jsonl")
FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "demo"
DEMO_IMAGE = "demo:base-image"


def _receipt_line(r) -> str:
    tag = " [DEMO]" if r.demo else ""
    unresolved = " [unresolved]" if r.unresolved else ""
    return (
        f"{r.receipt_id[:8]}  {r.task}#{r.run_seq}  {r.status:<8} "
        f"exit={r.exit_code}  state={r.state}{unresolved}{tag}"
    )


def _cmd_demo(args) -> int:
    report = run_demo(FIXTURE_DIR, args.ledger)
    for line in report["lines"]:
        print(line)
    print(
        f"[DEMO] ledger: {report['receipts_issued']} receipts | "
        f"adopted={report['decisions']['adopted']} rejected={report['decisions']['rejected']} "
        f"(the rest remain pending on the ledger)"
    )
    return 0


def _api_key() -> str | None:
    """NEBIUS_API_KEY env first; fall back to the `contree auth` profile
    token (~/.config/contree/auth.ini) — one credential covers both the
    sandbox CLI and the Token Factory inference API."""
    key = os.environ.get("NEBIUS_API_KEY")
    if key:
        return key
    try:
        import configparser
        ini = configparser.ConfigParser()
        ini.read(Path.home() / ".config" / "contree" / "auth.ini")
        return ini["profile:default"]["token"]
    except Exception:
        return None


def _cmd_run(args) -> int:
    api_key = _api_key()
    if not api_key:
        print("error: NEBIUS_API_KEY not set — live runs need Token Factory credentials.")
        print("       for an offline walkthrough: runanchor demo")
        return 2
    driver = ContreeDriver(session=args.session)
    try:
        driver.use(args.image)
    except DriverError as e:
        print(f"error: could not select image {args.image}: {e}")
        return 1
    planner = NemotronPlanner(api_key=api_key, model=args.model, seed=args.seed)
    ledger = Ledger(args.ledger)
    series = run_loop(
        driver, ledger, planner, task=args.task,
        max_iter=args.max_iter, model=args.model, seed=args.seed,
    )
    if not series:
        print("no runs executed")
        return 1
    for r in series:
        print(_receipt_line(r))
    last = ledger.get(series[-1].receipt_id)
    if last.unresolved:
        print(f"gave up after {len(series)} runs — last receipt marked unresolved")
    return 0


def _cmd_list(args) -> int:
    ledger = Ledger(args.ledger)
    receipts = ledger.all()
    if not receipts:
        print("no receipts on the ledger")
        return 0
    for r in receipts:
        print(_receipt_line(r))
    return 0


def _cmd_show(args) -> int:
    ledger = Ledger(args.ledger)
    r = ledger.resolve(args.receipt_id)
    if r is None:
        print(f"error: no receipt matching {args.receipt_id}")
        return 1
    d = r.to_dict()
    if r.demo:
        print("== DEMO receipt (fixture-anchored, not a live run) ==")
    for k in ("receipt_id", "task", "run_seq", "state", "status", "exit_code",
              "command", "cwd", "operation_uuid", "image_uuid", "result_image_uuid",
              "anchor_source", "stdout_sha256", "stderr_sha256", "stdout_tail",
              "stderr_tail", "diff_sha256", "files",
              "duration_s", "consumed_cpu_s", "consumed_memory", "consumed_memory_unit",
              "model", "seed", "seed_note", "unresolved", "warnings",
              "verification", "issued_at", "decision"):
        print(f"{k}: {d[k]}")
    return 0


def _cmd_decide(args, ledger: Ledger, state: str, by: str, reason) -> int:
    r = ledger.resolve(args.receipt_id)
    if r is None:
        print(f"error: no receipt matching {args.receipt_id}")
        return 1
    try:
        if state == "rejected":
            Gate(ledger).reject(r.receipt_id, by=by, reason=reason)
            print(f"rejected {r.receipt_id[:8]}")
        else:
            Gate(ledger).approve(r.receipt_id, by=by, reason=reason)
            print(f"adopted {r.receipt_id[:8]}")
    except (ValueError, Exception) as e:  # InvalidTransition / missing reason
        print(f"error: {e}")
        return 1
    return 0


def _cmd_approve(args) -> int:
    return _cmd_decide(args, Ledger(args.ledger), "adopted", "human", args.reason)


def _cmd_reject(args) -> int:
    reason = args.reason if args.reason is not None else input("reason: ")
    return _cmd_decide(args, Ledger(args.ledger), "rejected", "human", reason)


def _cmd_verify(args) -> int:
    ledger = Ledger(args.ledger)
    r = ledger.resolve(args.receipt_id)
    if r is None:
        print(f"error: no receipt matching {args.receipt_id}")
        return 1
    if args.driver == "demo":
        driver = DemoDriver.from_dir(FIXTURE_DIR / "verify")
    else:
        if not _api_key():
            print("error: NEBIUS_API_KEY not set — live verify needs credentials.")
            print("       hint: --driver demo replays the recorded fixture")
            return 2
        driver = ContreeDriver(session=args.session)
    try:
        result = verify_receipt(r, driver)
    except DriverError as e:
        print(f"verify failed: {e}")
        return 1
    print(f"{result.verdict}  ({r.receipt_id[:8]})")
    for name, diff in result.diffs.items():
        print(f"  {name}: expected={diff['expected']} actual={diff['actual']}")
    if result.replay_operation_uuid:
        print(f"  replay anchored to op {result.replay_operation_uuid}"
              f" ({result.replay_anchor_source})")
    # the verification attempt itself is evidence — record every verdict
    ledger.record_verification(
        r.receipt_id, result.verdict, result.diffs,
        replay_operation_uuid=result.replay_operation_uuid,
        replay_anchor_source=result.replay_anchor_source,
    )
    if result.verdict == "mismatch":
        try:
            ledger.decide(r.receipt_id, "mismatch", by="verifier",
                          reason="replay differs from recorded receipt")
        except InvalidTransition:
            pass  # already mismatch (re-verify) — evidence recorded above
    return 0 if result.verdict == "match" else 1


def _cmd_bench(args) -> int:
    api_key = _api_key()
    if not api_key:
        print("error: NEBIUS_API_KEY not set — bench is live measurement (sandbox + judge calls).")
        print("       for an offline walkthrough: runanchor demo")
        return 2
    from .bench import run_bench
    from .judge import NemotronJudge

    judge = NemotronJudge(api_key=api_key, model=args.model)

    def driver_for(item):
        d = ContreeDriver(session=f"{args.session}-{item.slug}")
        d.use(args.image)
        return d

    def planner_for(item):
        return NemotronPlanner(api_key=api_key, model=args.model)

    report = run_bench(
        args.corpus, Ledger(args.ledger),
        driver_for=driver_for, planner_for=planner_for, judge=judge,
        max_iter=args.max_iter,
    )
    for line in report.lines:
        print(line)
    if args.out:
        Path(args.out).write_text(json.dumps(
            {"matrix": asdict(report.matrix), "rows": report.rows,
             "sensitivity": report.sensitivity, "specificity": report.specificity},
            indent=2))
        print(f"report written: {args.out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="runanchor",
                                description="Verification and approval gate for coding-agent runs")
    p.add_argument("--ledger", default=str(DEFAULT_LEDGER), help="ledger path (default: state/receipts.jsonl)")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("demo", help="offline walkthrough on recorded fixtures")

    bench = sub.add_parser("bench", help="measurement: run labeled corpus, report sensitivity/specificity (live)")
    bench.add_argument("--corpus", default=str(Path(__file__).resolve().parent.parent / "corpus"))
    bench.add_argument("--session", default="runanchor-bench")
    bench.add_argument("--image", default="python:3.12-slim")
    bench.add_argument("--model", default="nvidia/Nemotron-3_5-Lightning")
    bench.add_argument("--max-iter", type=int, default=5)
    bench.add_argument("--out", default=None, help="write the report JSON here")

    run = sub.add_parser("run", help="run an agent task (live: needs NEBIUS_API_KEY)")
    run.add_argument("task")
    run.add_argument("--session", default="runanchor")
    run.add_argument("--image", default="python:3.12-slim")
    run.add_argument("--model", default="nvidia/Nemotron-3_5-Lightning")
    run.add_argument("--max-iter", type=int, default=5)
    run.add_argument("--seed", type=int, default=None,
                     help="recorded on receipts; NOT a replay guarantee (API ignores it)")

    sub.add_parser("list", help="list receipts")
    show = sub.add_parser("show", help="show a receipt (full id or unique prefix)")
    show.add_argument("receipt_id")

    approve = sub.add_parser("approve", help="adopt a pending receipt")
    approve.add_argument("receipt_id")
    approve.add_argument("--reason", default=None)

    reject = sub.add_parser("reject", help="reject a pending receipt (reason required)")
    reject.add_argument("receipt_id")
    reject.add_argument("--reason", default=None)

    verify = sub.add_parser("verify", help="replay-verify a receipt")
    verify.add_argument("receipt_id")
    verify.add_argument("--driver", choices=["live", "demo"], default="live")
    # separate session so verify's image fork doesn't rewind the work session
    verify.add_argument("--session", default="runanchor-verify")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "demo":
        return _cmd_demo(args)
    if args.cmd == "run":
        return _cmd_run(args)
    if args.cmd == "list":
        return _cmd_list(args)
    if args.cmd == "show":
        return _cmd_show(args)
    if args.cmd == "approve":
        return _cmd_approve(args)
    if args.cmd == "reject":
        return _cmd_reject(args)
    if args.cmd == "verify":
        return _cmd_verify(args)
    if args.cmd == "bench":
        return _cmd_bench(args)
    build_parser().print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
