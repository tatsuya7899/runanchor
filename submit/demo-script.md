# runanchor — demo video script (target ≤ 3:00)

## 0:00–0:15 — Hook (title card + voiceover)

> "AI agents say 'done, tests pass.' Who checks that? CI checks artifacts —
> nobody checks the agent's report. runanchor does."

Show terminal, empty directory.

## 0:15–0:45 — Offline demo (proves the whole flow, no credentials)

```bash
runanchor demo
```

Narrate while it runs: agent series red → red → green; a receipt per run,
each anchored to a provider operation ID; the green receipt is replay-verified
→ `match`; the false-claim run is rejected with a reason; everything stays on
the ledger.

```bash
runanchor list
runanchor show <receipt-id>   # point at operation_uuid, anchor_source,
                              # fingerprints, decision fields
```

## 0:45–1:30 — Verify in action (two axes)

Explain: the receipt stores the start image UUID AND the result image UUID.
Verify runs two independent checks:

- **Replay**: fork the recorded start image, rerun the recorded command,
  compare exit code + normalized output fingerprints. Show a `match`: "the
  claim reproduced — adoptable evidence." Narrate the `mismatch` path: "if
  the rerun differs, the receipt turns mismatch on the ledger — and a human
  still decides, because a mismatch is evidence, not a verdict."
- **Hidden oracle**: fork the produced *result* image, mount a test suite the
  agent never saw — at an unpredictable path *outside* its workspace, run by
  an isolated interpreter, so nothing it wrote can shadow the check. "A green
  log can be honest or lucky — this checks the state, not the story."

## 1:30–2:15 — Measured gate quality

```bash
python3 scripts/bench_live_runanchor.py --planner-model nvidia/nemotron-3-super-120b-a12b \
    --judge-model nvidia/Nemotron-3_5-Lightning --max-iter 8 \
    --ledger eval/bench-ledger-new.jsonl --out eval/bench-new.json
```

> "We don't ask you to trust our gate either. Here's the labeled corpus —
> 39 seeded traps, 15 clean — the judge prompt, and the exact commands.
> Two numbers, not one: reading evidence alone, the judge caught 7 of 11
> defective runs; with replay + the hidden oracle, the gate caught all 11 —
> while passing 42 of 43 good runs. The corpus is committed; run it
> yourself, check our numbers."

Show the two-layer confusion matrix output. Show `app/corpus/<item>/oracle/`
briefly — "the ground truth here is executable, not a label".

## 2:15–2:45 — Under the hood

Show architecture diagram (docs/architecture.svg):

- ConTree/Sandboxes ops → receipt (provider-issued anchor)
- append-only hash-chained ledger
- Nemotron planner (agent loop) + Nemotron judge (measurement), both via
  Token Factory inference
- seed caveat callout: "seed recorded, not trusted — the API isn't
  deterministic, we measured it"

## 2:45–3:00 — Close

> "runanchor: receipts anchored to the provider, replays before approval, an
> audit trail that keeps the failures too. MIT licensed, offline demo in the
> repo — check our numbers, not our claims."

End card: repo URL + "Nebius × NVIDIA Global AI Hackathon".
