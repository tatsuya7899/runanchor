# runanchor

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

> **Status: pending live validation.** The measurement harness, corpus and
> judge prompt are committed and reproducible (see *Reproduce the measurement*
> below), but headline numbers require a live Nebius Sandboxes run — currently
> awaiting closed-beta access. The offline demo and full test suite work today.

| metric | value | how it was measured |
|--------|-------|---------------------|
| sensitivity (bad runs caught) | _pending_ | labeled seeded corpus, n=24 |
| specificity (good runs passed) | _pending_ | clean control tasks, n=11 |
| cost per measured run | _pending_ | Token Factory usage records |

We publish these numbers only after measuring them ourselves — and you can
re-run the same procedure rather than trusting ours.

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
  or machine judge   rerun command, compare exit code
        │            + stream fingerprints + result image
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
