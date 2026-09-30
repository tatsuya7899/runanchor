# Token Factory / NVIDIA feedback — runanchor

## What worked well

- **OpenAI-compatible inference endpoint**: `api.tokenfactory.nebius.com` took
  the same API key as `contree auth` — zero extra auth plumbing.
- **`contree` CLI design**: `-o json`, `op show`, `use <image>` map cleanly
  onto a verification tool's needs (operation records, image forking).
- **Nemotron-3_5-Lightning**: fast and very cheap (~$0.06/$0.24 per 1M tokens)
  — realistic as a measurement judge. For the agent-loop planner we switched
  to `nemotron-3-super-120b-a12b`: Lightning tended to loop on inspection
  commands instead of editing (worth documenting which model class works for
  agentic loops vs one-shot judgment).

## Friction / findings worth sharing

- **Sandboxes is a closed beta**: `contree auth` accepted the token but every
  call returned 403 until the beta form was submitted — the CLI's own warning
  was accurate and helpful, but the docs could state the beta gate upfront.
- **`seed` is accepted but not deterministic**: identical request + identical
  seed returned different outputs (3 calls measured, 2026-09-29). If
  determinism isn't a goal, the docs should say so; if it is, it doesn't yet
  work. We record seed as metadata only.
- **`result_image_uuid` is not replay-stable across sessions**: identical
  command + identical start image in two different sessions produced different
  result image UUIDs (measured 2026-09-30). Within one session the same
  command cached to the same UUID. If checkpoints are meant to be
  content-addressed, session lineage is leaking into them; if not, the docs
  should state that image UUIDs are not comparable across sessions.
- **`run -D` (disposable) never produces a result image** (`result_image_uuid:
  null`) — correct once known, but it changes which runs you can fork a result
  from. Documenting "non-disposable = checkpoint, disposable = none" upfront
  would have saved us an assumption.
- **Reasoning models + `max_tokens`**: Lightning is reasoning-oriented and
  reasoning consumes the token budget — structured-output consumers must
  budget headroom and parse the *last* JSON object, not the first. A note in
  the JSON-mode docs would save integrators a failed afternoon.
- **Cost observability**: for a tool like ours, per-operation resource/cost
  fields on `op show` are exactly the anchor data we need — keeping them
  complete and documented matters.
- **Docs we relied on**: Sandboxes CLI reference, inference quickstart,
  SWE-agents/SWE-bench environment docs — mostly accurate where we could
  verify; a published JSON schema for `op show` / `op events` output would
  remove guesswork.
