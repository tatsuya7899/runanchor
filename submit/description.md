# runanchor — submission description

## What it is

runanchor is a verification and approval gate for coding-agent runs.

Coding agents now write, run, and test code autonomously — but when an agent
reports "done, tests pass", nothing checks the report itself. CI distrusts
artifacts; nothing distrusts the agent's *account of what happened*. Teams
pay for that gap with a human re-running everything by hand.

runanchor closes it. Every agent run inside a Nebius Sandboxes environment is
issued a **receipt anchored to provider-issued execution records** — the
sandbox operation UUID and image IDs, not the agent's self-report. A receipt
is then verified on two axes: **replay** forks the recorded start image and
reruns the recorded command, comparing exit code and normalized output
fingerprints; a **hidden oracle** forks the produced *result* image and runs
a test suite the agent never saw — catching hardcoded answers, dropped
boundaries and latent spec violations that a green log cannot show. Runs
become *adopted* only after a human or a measured machine judge approves
them; rejected, mismatched and unresolved runs stay on an append-only,
hash-chained ledger — evidence that never silently disappears.

## Why it matters

- **Provider-issued anchor**: receipts reference ConTree operation UUIDs and
  image IDs — attestations the agent cannot fabricate.
- **Verify before approve**: replaying from the recorded environment catches
  "reported-but-not-run" claims that look perfect in a log; the hidden oracle
  catches "green-but-wrong" states that look perfect even in a real log.
- **Measured, not asserted**: sensitivity/specificity are measured on a
  published labeled corpus (24 seeded-trap cases + 11 clean controls) where
  the ground truth is executable — the oracle's exit code on the produced
  state, not the planted label. Two layers are reported separately: judge on
  evidence alone, and judge + replay + oracle. The full measurement — corpus,
  judge prompt, command sequence — is committed so anyone can reproduce it
  (you verify our numbers, not trust them).

## What it does NOT do (honest limits)

- It moves trust to the provider's records; provider-side faults are out of
  scope and stated as such.
- A replay mismatch is evidence for review, not proof of deception — flaky
  outputs legitimately differ, so mismatches stay overridable by humans.
- `seed` is recorded as metadata only: Token Factory's API does not reproduce
  outputs for identical seeds (measured), so verification never relies on it.

## Stack

- **Nebius Token Factory / ConTree (Sandboxes)**: isolated sandbox runs,
  operation/image records as the provider anchor — via the `contree` CLI.
- **NVIDIA Nemotron via Token Factory inference** (OpenAI-compatible):
  `nvidia/nemotron-3-super-120b-a12b` drives the agent-loop planner;
  `nvidia/Nemotron-3_5-Lightning` is the measurement judge.
- Python, zero runtime deps beyond the contree CLI; receipts on an
  append-only JSONL ledger.

## Try it

```bash
pip install . && runanchor demo        # offline walkthrough, no credentials
python3 scripts/verify.py              # full offline suite, no network
```

`demo` replays recorded sandbox operations end-to-end with no credentials —
receipts clearly marked fixture-derived.
