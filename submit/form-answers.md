# 提出フォーム転記 — runanchor(Nebius × NVIDIA Global AI Hackathon)

※フォーム各欄への転記用。見出しは欄名、本文をそのまま貼る。提出物は英語。
Devpost側の欄構成はフォーム画面で確認して合わせること。`OWNER ACTION
REQUIRED` は公開操作(動画投稿・repo公開)後にURLへ置き換えること
(置き忘れは提出不可 — ready.pyで検査)。

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
operation/image records; inference API — nvidia/nemotron-3-super-120b-a12b
drives the agent planner, nvidia/Nemotron-3_5-Lightning is the measurement
judge). Python, MIT license.

============================================================
Measured results (if the form has a results/metrics field)
============================================================
Gate (evidence + replay + hidden oracle): sensitivity **100% (7/7)**,
specificity **86% (24/28)**.
Evidence-only judge baseline on the same 35 run series: 86% (6/7) / 89%
(25/28) — verification turned one adopted bad run into a catch and rescued
one wrongly-rejected good run.
Ground truth is executable: a hidden test suite the agent never saw runs
against the produced result image (defective=7, good=28 — the planted label
is only a fallback).
Cost: sandbox free during beta, ≤10 model calls per item (planner ≤8 +
judge ×2). Measured 2026-09-30 on live Nebius Sandboxes; every run, replay
and oracle execution is anchored to a ConTree operation UUID in
eval/bench-ledger-20260930-v2.jsonl (hash-chain check: `runanchor check`).
Caveat stated plainly: 7/7 is "every defective run the corpus produced",
not a rate guarantee at scale.

============================================================
Demo video (YouTube URL)
============================================================
OWNER ACTION REQUIRED — URL to be added once the video is recorded and
uploaded (external publish needs explicit human approval).
script: submit/demo-script.md · narration claims: submit/narration-claims.md
· recorder: scripts/record_demo.py

============================================================
Repository URL (public, OSS license)
============================================================
OWNER ACTION REQUIRED — URL to be added once the repository is made public
(external publish needs explicit human approval). MIT license is committed
(LICENSE).

============================================================
Feedback on the tools
============================================================
(paste submit/feedback.md)
