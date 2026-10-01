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
Gate (evidence + replay + hidden oracle): sensitivity **100% (11/11)**,
specificity **98% (42/43)** — Wilson 95% CIs [74%, 100%] and [88%, 100%]
respectively.
Evidence-only judge baseline on the same 54 run series: 64% (7/11) / 91%
(39/43) — verification turned four green-looking misses into catches and
flipped three borderline rejects to adopt. The single false reject is a
demonstrated-run boundary: the produced state passed the oracle, but the
run's own receipt ended on `Permission denied` — the suite never
demonstrably ran green.
Ground truth is executable: a hidden test suite the agent never saw runs
against the produced result image (defective=11, good=43 — all truths
oracle-derived, no label fallback this run; two of the defective rows are
clean items whose honest fixes simply failed the oracle). The oracle mounts
outside the workspace at an unpredictable path under an isolated
`python3 -I -S` runner, so the agent's own files cannot shadow or poison
the check.
Cost: 455 anchored ledger snapshots — $0 during the ConTree beta; measured
billing: **$0.30 total project inference through 10-01** (Token Factory
console; v4 increment est. ~$0.4; breakdown in eval/bench-20261001-v4.md).
Measured 2026-10-01 on live Nebius Sandboxes; every run, replay and oracle
execution is anchored to a ConTree operation UUID in
eval/bench-ledger-20261001-v4.jsonl (hash-chain check: `runanchor check`).
Caveats stated plainly: 11/11 is "every defective run this corpus
produced", not a rate guarantee at scale; judge-output health is
disclosed — 0/108 unparseable verdicts (an earlier harness run had 6/70
fail-safe rejects, now retried and counted separately).

============================================================
Demo video (YouTube URL)
============================================================
https://youtu.be/Z-NM0GLORFA

**Video file: `submit/runanchor-demo.mp4`** (2:04, 1920×1080 H.264+AAC,
narration by owner — rendered by `scripts/render_demo_video_runanchor.py`,
no screen capture needed; re-render to replace).
script: submit/narration-text.md (rendered cut) · storyboard: submit/demo-script.md
· narration claims: submit/narration-claims.md

============================================================
Repository URL (public, OSS license)
============================================================
https://github.com/tatsuya7899/runanchor

MIT license is committed (LICENSE).

============================================================
Feedback on the tools
============================================================
(paste submit/feedback.md)
