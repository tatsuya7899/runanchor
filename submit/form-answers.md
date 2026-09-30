# 提出フォーム転記 — runanchor(Nebius × NVIDIA Global AI Hackathon)

※フォーム各欄への転記用。見出しは欄名、本文をそのまま貼る。提出物は英語。
Devpost側の欄構成はフォーム画面で確認して合わせること。`_pending_` は
提出直前に実測値/URLへ置き換えること(置き忘れは提出不可 — ready.pyで検査)。

============================================================
Project name
============================================================
runanchor — receipts your coding agent can't fake

============================================================
Tagline / elevator pitch
============================================================
CI distrusts artifacts. Nothing distrusts an agent's report — until now.
Every agent run gets a receipt anchored to the provider's own execution
record, replay-verified before a human or measured judge approves it.

============================================================
Description / About this project
============================================================
(paste submit/description.md — sections "What it is" / "Why it matters" /
"What it does NOT do" / "Stack" / "Try it")

============================================================
Built with / tech stack
============================================================
Nebius Token Factory (ConTree Sandboxes — isolated runs + provider-issued
operation/image records; inference API — NVIDIA Nemotron-3_5-Lightning for
the agent planner and the measurement judge). Python, MIT license.

============================================================
Measured results (if the form has a results/metrics field)
============================================================
sensitivity: **46% (11/24)** | specificity: **91% (10/11)** |
cost: sandbox free during beta, ≤9 model calls per item
(measured 2026-09-30 on live Nebius Sandboxes — 24 seeded + 11 clean
labeled corpus; every run anchored to a ConTree operation UUID in
eval/bench-ledger.jsonl. The 46% miss rate is the product thesis made
measurable: a judge reading receipt evidence alone cannot see latent
deception behind a green stdout tail — replay verification exists to
catch exactly that layer)

============================================================
Demo video (YouTube URL)
============================================================
_pending_ — script: submit/demo-script.md, narration claims:
submit/narration-claims.md, recorder: scripts/record_demo.py

============================================================
Repository URL (public, OSS license)
============================================================
_pending_ — MIT license committed (LICENSE)

============================================================
Feedback on the tools
============================================================
(paste submit/feedback.md)
