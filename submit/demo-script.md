# runanchor — demo video script (target ≤ 3:00)

## 0:00–0:15 — Hook (title card + voiceover)

> "AI agents say 'done, tests pass.' Who checks that? CI checks artifacts —
> nobody checks the agent's report. runanchor does."

Show terminal, empty directory.

## 0:15–0:45 — Offline demo (proves the whole flow, no credentials)

```bash
python3 -m runanchor.cli --ledger demo.jsonl demo
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

## 0:45–1:30 — Verify in action

Explain: the receipt stores the start image UUID. Verify forks that recorded
environment and reruns the recorded command — exit code + output fingerprints
compared against the original.

- Show a `match`: "the claim reproduced — adoptable evidence."
- Then show or narrate the `mismatch` path: "if the rerun differs, the receipt
  turns mismatch on the ledger — and a human still decides, because a mismatch
  is evidence, not a verdict."

## 1:30–2:15 — Measured gate quality

```bash
runanchor bench --corpus app/corpus
```

> "We don't ask you to trust our gate either. Here's the labeled corpus —
> 24 seeded bad runs, 11 clean — the judge prompt, and the exact commands.
> Our sensitivity/specificity: <MEASURED>. Regenerate the corpus, run it
> yourself, check our numbers."

Show the confusion matrix output. Show `app/corpus/<item>/label.json` briefly.

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
