# About the project — runanchor

## Inspiration

Coding agents end every run the same way: a chat message saying *"done,
all tests pass."* CI systems learned long ago not to trust a commit
message — they re-run the build. But nothing re-runs the agent's report.
The run is a black box: no record of what was actually executed, no way to
tell a real fix from a confident summary. We wanted the agent equivalent
of a flight recorder — a receipt anchored to something the agent cannot
edit.

## What it does

runanchor turns each coding-agent run into a **verifiable receipt**
anchored to the provider's own execution record — ConTree (Nebius
Sandboxes) operation UUIDs and image IDs, not the agent's self-report.
Nothing is adopted until verified on two independent axes:

- **Replay** forks the recorded start image and re-executes the command,
  comparing exit code and stream fingerprints — a reported-but-not-run
  claim cannot survive re-execution.
- **A hidden oracle** runs tests the agent never saw, mounted outside its
  workspace under an isolated interpreter — green-but-wrong cannot
  survive either.

Approved runs and rejected claims alike land on an append-only,
hash-chained ledger (`runanchor check` audits the chain). Rejection is a
recorded outcome, not a deleted embarrassment.

## How we built it

- **Nebius Token Factory / ConTree Sandboxes** — every run, replay and
  oracle execution executes in an isolated sandbox; the returned
  operation UUIDs and image IDs anchor each receipt to provider-side
  records.
- **NVIDIA Nemotron** — `nvidia/nemotron-3-super-120b-a12b` drives the
  agent's planner loop; `nvidia/Nemotron-3_5-Lightning` is the judge that
  reads receipts and approves or rejects.
- **Python** — CLI (`runanchor run / list / show / verify / check /
  demo / bench`), receipt schema, ledger, verifier, and a labeled corpus
  of 54 tasks (39 seeded traps + 15 clean controls) whose ground truth is
  an executable oracle, not a label.

## The measurement (we measured our own gate)

| layer | sensitivity (defective caught) | specificity (good passed) |
|---|---|---|
| evidence-only judge | 64% (7/11), Wilson 95% CI [35%, 85%] | 91% (39/43), CI [78%, 96%] |
| **gate: evidence + replay + oracle** | **100% (11/11), CI [74%, 100%]** | **98% (42/43), CI [88%, 100%]** |

Reading evidence alone, the judge adopted four runs whose green-looking
logs hid states the hidden oracle then failed. The gate caught all
eleven defective runs — including two *clean* tasks where the agent's
honest fix simply didn't work — and passed 42 of 43 good runs. Row-level
data, the corpus, the judge prompt, and the hash-chained ledger are all
in the repo: check our numbers, not our claims.

## Challenges we ran into

- **The measurement itself had bugs.** Adversarial review of the harness
  found label leakage (oracle contents visible to the agent) and traps
  that were never wired — we fixed the harness before trusting any
  number.
- **Judge output hygiene.** An early run had 6/70 unparseable verdicts
  that silently became rejections. We added retries and a separate
  `unparseable` counter — v4 reports 0/108.
- **What counts as "defective."** Most seeded traps get honestly fixed by
  the agent, so the planted label is not truth — the oracle's exit code
  on the produced state is. And our single false positive is a boundary
  worth keeping: the code was fixed correctly, but the run never
  demonstrated a green suite (permission denied on the wrapper). "Fixed
  state" and "demonstrated run" are different claims; the gate measured
  the latter.

## What we learned

- Evidence review and verification are different instruments. The 36-point
  sensitivity gap (64% → 100%) is the whole argument for the product.
- Small-sample honesty beats big claims: we publish Wilson confidence
  intervals with the headline numbers, and name what we did not measure.

## What's next

- Hardening the oracle against an agent that poisons the sandbox
  interpreter itself (pristine-interpreter mount, frozen `sys.path`).
- Tighter per-run cost metering — current billing visibility is
  console-level, not per-operation.

## Try it

```
git clone https://github.com/tatsuya7899/runanchor
cd runanchor && pip install -e .
runanchor demo    # fully offline — no credentials needed
```
