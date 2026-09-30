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
> `eval/bench-20260930.json` + `eval/bench-ledger.jsonl` (every run anchored
> to a real ConTree operation UUID — inspectable via `contree op show`).

| metric | value | how it was measured |
|--------|-------|---------------------|
| sensitivity (bad runs caught) | **46%** (11/24) | labeled seeded corpus, n=24 |
| specificity (good runs passed) | **91%** (10/11) | clean control tasks, n=11 |
| cost per measured item | sandbox free during beta; ≤9 model calls/item | 35 items, planner=Nemotron-Super-120B, judge=Nemotron-Lightning |

**Why 46% is the headline, not a disclaimer:** a judge reviewing receipt
evidence alone misses subtle deceptions — hardcoded passing cases,
state-dependent tests, latent spec violations look identical to real fixes in
a stdout tail. That miss is exactly what replay verification exists to catch:
re-executing from the recorded image detects evidence the report glossed
over. Most judge rejections were *insufficient evidence* — conservative and
correct for a gate, but not yet proof of detection. Row-level detail and the
bug-type breakdown live in `eval/bench-20260930.md`.

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
                        exit code, stream fingerprints, diff hash,
                        cost metadata, model+seed metadata
                 │
        ┌────────┴─────────┐
        ▼                  ▼
  human approve      verify: fork recorded image,
  or machine judge   rerun command disposable,
        │            compare exit code + stream fingerprints
        ▼                  │
   append-only ledger ◄────┘
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
| ConTree `op events` (log stream) | `ContreeDriver.events()` | fixture + type-guard tests | command exists; payload unverified |
| ConTree `session delete` (verify-session cleanup) | `ContreeDriver.close()` | call-shape + cleanup-on-failure tests | ✅ 2026-09-30 — probe sessions deleted after verify |
| `result_image_uuid` comparison | **dropped axis** | — | ✅ disproven 2026-09-30: checkpoints are not reproducible across sessions (identical command + identical start image → different UUIDs `9d2dfa13…` vs `e82f0702…`); comparing them would false-mismatch every honest run |
| Token Factory chat completions — agent planner | `NemotronPlanner` (`agent_loop.py`) | action-parse, task-injection tests | ✅ 2026-09-29 (minimal call ≈ $0.000004) |
| Token Factory chat completions — measurement judge | `NemotronJudge` (`judge.py`) | verdict-parse + secret-scrub tests | ✅ same API key, same endpoint |
| `seed` parameter | planner/judge + `Receipt.seed` | seed-note metadata only | ✅ tested: accepted but **not deterministic** |

## Demo (no credentials, no network)

```bash
python3 -m runanchor.cli --ledger /tmp/demo.jsonl demo
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
runanchor run "fix the failing tests" --image python:3.12-slim
runanchor list                          # every run, including failures
runanchor show <receipt-id>             # evidence + anchor
runanchor verify <receipt-id>           # fork recorded image, replay, compare
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
python3 scripts/build_corpus.py      # regenerate the labeled corpus (35 items)
runanchor bench --corpus app/corpus --out report.json   # live run (needs keys)
```

- corpus: `app/corpus/` — 24 seeded bad-run cases + 11 clean controls, each
  with `label.json` (label, bug_type, mode, oracle/ground truth) and a
  `seed/` workspace
- judge prompt: `app/runanchor/judge.py` (`JUDGE_SYSTEM`)
- decision rule: judge sees receipt evidence only (task, command, exit code,
  log tail, diff fingerprint, status) — labels never leak into evidence
- reproduction check: `python3 scripts/verify.py` runs the full offline suite
  (94 tests) with no network and no credentials

## Repository layout

```
app/runanchor/     domain + drivers + cli (receipt, ledger, verifier, gate,
                   agent_loop, judge, bench, demo, sanitize)
app/tests/         offline test suite (no network)
app/corpus/        labeled measurement corpus
app/fixtures/demo/ recorded ops for --demo replay
scripts/           verify.py, build_corpus.py, ready.py
bd/                design history (Japanese)
research/          provider API investigation notes
submit/            hackathon submission text + demo script
```

## License

MIT — see `LICENSE`.
