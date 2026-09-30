# runanchor

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

**CI distrusts artifacts. Nothing distrusts an agent's *report*.**

runanchor is a verification and approval gate for coding-agent runs. When an
agent says *"fixed it, tests pass"*, runanchor doesn't take the report at face
value: every run is issued a **receipt anchored to provider-issued execution
records** (sandbox operation UUID + image IDs), can be **replayed** from the
recorded environment, and only becomes *adopted* after a human — or a measured
machine reviewer — approves it. Rejected and failed runs stay on an append-only
ledger instead of disappearing.

Built for the **Nebius × NVIDIA Global AI Hackathon** (Coding & Agentic
Engineering track).

## Measured gate quality

> **Measured 2026-09-30 on live Nebius Sandboxes** (beta). Row-level results:
> `eval/bench-20260930-v2.json` + `eval/bench-ledger-20260930-v2.jsonl` —
> every run, replay, and oracle execution anchored to a real ConTree
> operation UUID (inspectable via `contree op show`; audit the ledger with
> `runanchor check --ledger <file>`).

Two layers measured on the **same 35 run series**; ground truth is the
executable hidden oracle run against each produced result image (defective
=7, good =28 — the planted label is only a fallback):

| layer | sensitivity (defective caught) | specificity (good passed) |
|-------|-------------------------------|---------------------------|
| evidence-only judge (baseline) | 86% (6/7) | 89% (25/28) |
| **gate: evidence + replay + oracle** | **100% (7/7)** | **86% (24/28)** |

| cost per measured item | value |
|------------------------|-------|
| sandbox ops | free during beta |
| model calls | ≤10/item (planner ≤8, judge ×2) |
| planner / judge | nemotron-3-super-120b-a12b / Nemotron-3_5-Lightning |

**What the layers mean:** evidence-only review already stops most bad runs —
a gate refusing unproven claims is conservative by design. But it adopted one
run whose visible suite never exercised the planted trap
(`seeded-skip-tests-tempt`); the hidden oracle failed it, and the gate
rejected. Verification also flipped one honest run from reject to adopt.
The cost: verification made the judge *more* conservative on two good runs
(gate fp=4 vs baseline fp=3). Row-level detail: `eval/bench-20260930-v2.md`.

Honest caveats: 100% is a small-denominator measurement (7 defective), not a
rate guarantee — claim: "every defective run the corpus produced was caught".
Most seeded items were honestly fixed by the planner, which is why truth is
the oracle's exit code and not the trap label.

We publish only numbers we measured — and you can re-run the same procedure
rather than trusting ours (`scripts/bench_live_runanchor.py`).

## Why not just trust the agent's log?

Three failure families runanchor is built to stop:

- **reported-but-not-run** — "tests pass" where no test execution happened
- **green-but-wrong** — real green output hiding a boundary/spec violation
- **self-graded evidence** — the agent wrote the tests it cites, or weakened
  the oracle to reach green

## How it works

```
agent task ──► sandbox run (ConTree / Nebius Sandboxes)
                 │
                 ▼
        receipt issued ── operation_uuid (provider-issued)
                        image_uuid / result_image_uuid
                        exit code, stream fingerprints,
                        cost metadata, model+seed metadata
                 │
        ┌────────┴──────────────┐
        ▼                       ▼
  human approve           verify, two axes:
  or machine judge        ① replay — fork the recorded start image,
        │                    rerun the command disposable, compare
        │                    exit code + stream fingerprints
        │                  ② hidden oracle — fork the RESULT image,
        │                    mount tests the agent never saw,
        │                    run them against what it produced
        ▼                       │
   append-only ledger ◄─────────┘
   (pending → adopted / rejected / mismatch / unresolved;
    every snapshot kept, hash-chained, tamper-evident)
```

**What makes a receipt stronger than a log:** the anchor is issued by the
execution provider, not the agent. `anchor_source` marks how strong the anchor
is: `run-json` (UUID captured from the run response), `head` (weaker HEAD
fallback, flagged), `demo` (fixture-derived, never passes as live).

**Honest limit:** runanchor moves trust from the agent's claim to the
provider's records — it cannot detect provider-side faults. The receipts make
*what was attested by whom* inspectable instead of invisible.

## Token Factory / Nebius usage depth

Each primitive below lists where it lives in code and what evidence backs it.
"Live-verified" means an actual Token Factory / ConTree call was made; unit
coverage is the offline suite.

| primitive | where | evidence | live-verified |
|-----------|-------|----------|---------------|
| ConTree `run` (isolated sandbox exec) | `ContreeDriver.run()` | argv/anchor/degraded-run tests | ✅ 2026-09-30 — real schema parsed (flat + `metadata.result.*` nested), op `01a0f15b-…` |
| ConTree `op show` (operation record → receipt anchor) | `ContreeDriver.run()` fallback | uuid-capture, missing-field, `op show`-failure tests | ✅ 2026-09-30 — flat `result.{stdout,state.*}` shape measured |
| ConTree `use <image>` (fork recorded env) | `verifier` via `ContreeDriver.use()` | replay-path tests | ✅ 2026-09-30 — replay forked `4fa16c8f…`, verify verdict `match` (e2e `scripts/e2e_live_runanchor.py`) |
| ConTree `run -D` (disposable verify rerun) | `verify_receipt` | disposable-flag test | ✅ 2026-09-30 — `-D` returns `result_image_uuid: null`; replay uses `-D` (no checkpoint needed — see below) |
| ConTree `use <result_image>` + hidden oracle run | `verify_receipt` oracle stage | oracle-target, oracle-fail, oracle-error tests | ✅ 2026-09-30 — result image forked, `oracle/` mounted, pass/fail recorded w/ op UUID |
| ConTree `op events` (log stream) | `ContreeDriver.events()` | fixture + type-guard tests | command exists; payload unverified |
| ConTree `session delete` (verify-session cleanup) | `ContreeDriver.close()` | call-shape + cleanup-on-failure tests | ✅ 2026-09-30 — probe sessions deleted after verify |
| `result_image_uuid` comparison | **dropped axis** | — | ✅ disproven 2026-09-30: checkpoints are not reproducible across sessions (identical command + identical start image → different UUIDs `9d2dfa13…` vs `e82f0702…`); comparing them would false-mismatch every honest run |
| Token Factory chat completions — agent planner | `NemotronPlanner` (`agent_loop.py`) | action-parse, task-injection tests | ✅ 2026-09-29 (minimal call ≈ $0.000004) |
| Token Factory chat completions — measurement judge | `NemotronJudge` (`judge.py`) | verdict-parse + secret-scrub tests | ✅ same API key, same endpoint |
| `seed` parameter | planner/judge + `Receipt.seed` | seed-note metadata only | ✅ tested: accepted but **not deterministic** |

## Demo (no credentials, no network)

```bash
pip install .                 # installs the `runanchor` command
runanchor demo                # writes receipts to state/receipts.jsonl
# or without installing:
PYTHONPATH=app python3 -m runanchor.cli --ledger /tmp/demo.jsonl demo
```

Replays recorded sandbox operations through the same driver interface: an
agent series (red → red → green), a replay verification, and gate decisions —
ending with 3 receipts on the ledger (1 adopted, 1 rejected, 1 pending).
Demo receipts are visibly marked `[DEMO]` and can never masquerade as live
provider records.

## Live usage (needs Token Factory)

Prereqs:

```bash
pip install contree-cli
contree auth            # Token Factory API token + project ID
export NEBIUS_API_KEY=… # same Token Factory key, for inference calls
```

```bash
runanchor run "fix the failing tests" --image python:3.12-slim \
    --file ./seed/calc.py:/work/calc.py      # repeatable workspace mounts
runanchor list                          # every run, including failures
runanchor show <receipt-id>             # evidence + anchor
runanchor verify <receipt-id>           # replay from recorded start image
runanchor verify <receipt-id> --oracle-dir app/corpus/clean-basic/oracle
                                        # + hidden tests on the result image
runanchor check                         # ledger hash-chain integrity
runanchor approve <receipt-id>
runanchor reject <receipt-id> --reason "log claims green, rerun shows red"
```

Uses **NVIDIA Nemotron** models served by Nebius Token Factory (OpenAI-compatible
endpoint `https://api.tokenfactory.nebius.com/v1/chat/completions`) in two
places:

- **planner** — drives the agent loop (write → run → red → fix → green),
  default `nvidia/Nemotron-3_5-Lightning`
- **judge** — measurement-mode reviewer that sees receipt evidence only and
  returns a structured adopt/reject verdict

`--seed` is accepted and recorded on receipts as metadata; measured on
2026-09-29, the API returns different outputs for identical seeds — seed is
**not** a replay guarantee, and verification never relies on it.

## Reproduce the measurement

Everything needed is in this repo:

```bash
python3 scripts/build_corpus.py        # regenerate the labeled corpus (35 items)
python3 scripts/bench_live_runanchor.py \
    --planner-model nvidia/nemotron-3-super-120b-a12b \
    --judge-model nvidia/Nemotron-3_5-Lightning \
    --max-iter 8 --image runanchor-bench \
    --ledger eval/bench-ledger-new.jsonl --out eval/bench-new.json
```

- corpus: `app/corpus/` — 24 seeded-trap cases + 11 clean controls, each with
  `label.json` (label, bug_type, mode, oracle description), a `seed/`
  workspace, and a hidden `oracle/` test suite the agent never sees
- judge prompt: `app/runanchor/judge.py` (`JUDGE_SYSTEM`)
- decision rule: the judge sees receipt evidence only (task, every run's
  command/exit code/stdout+stderr tails, unresolved flag) plus — at the gate
  layer — the verification record (replay verdict, oracle outcome). Labels
  never leak into evidence, and every recorded decision carries the sha256 of
  the exact evidence payload it was judged on
- ground truth: the hidden oracle's exit code on the produced result image —
  a seeded item honestly fixed is a *good* run, a clean item left broken is
  *defective* (labels are the fallback only when no oracle can run)
- reproduction check: `python3 scripts/verify.py` runs the full offline suite
  with no network and no credentials; `scripts/validate_corpus.py` proves each
  oracle actually probes the seeded trap

## Repository layout

```
app/runanchor/     domain + drivers + cli (receipt, ledger, verifier, gate,
                   agent_loop, judge, bench, demo, sanitize)
app/tests/         offline test suite (no network)
app/corpus/        labeled measurement corpus
app/fixtures/demo/ recorded ops for `runanchor demo` replay
scripts/           verify.py, build_corpus.py, validate_corpus.py,
                   bench_live_runanchor.py, check_packaging.py, ready.py
bd/                design history (Japanese)
research/          provider API investigation notes
submit/            hackathon submission text + demo script
```

## License

MIT — see `LICENSE`.
