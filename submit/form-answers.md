# Devpost form answers — runanchor (Nebius × NVIDIA Global AI Hackathon)

Copy-paste source for the submission form: each section header is a form
field; paste the body as-is. Check the actual Devpost form layout when
submitting. `ready.py` verifies the submission URLs are filled.

============================================================
Project name
============================================================
runanchor — receipts your coding agent can't fake

============================================================
Tagline / elevator pitch (max 200 chars — this one is 169)
============================================================
Agents say "tests pass." Who checks? runanchor anchors every coding-agent
run to provider-issued execution records — replay-verified, oracle-tested,
adopted on evidence.

============================================================
Project Story — About the project (Markdown field)
============================================================
(paste the whole of submit/project-story.md — Inspiration / What it does /
How we built it / The measurement / Challenges / What we learned /
What's next / Try it)

============================================================
Built with / tech stack (tags — up to 25)
============================================================
python · nebius · nebius-token-factory · nebius-sandboxes · contree ·
nvidia · nemotron · ai-agents · code-verification · developer-tools

(Long prose version, if a free-text field instead of tags:)
Nebius Token Factory (ConTree Sandboxes — isolated runs + provider-issued
operation/image records; inference API — nvidia/nemotron-3-super-120b-a12b
drives the agent planner, nvidia/Nemotron-3_5-Lightning is the measurement
judge). Python, MIT license.

============================================================
"Try it out" links
============================================================
https://github.com/tatsuya7899/runanchor  (repo — offline demo inside:
`runanchor demo` runs with no credentials)

============================================================
Project media — image gallery (up to 15)
============================================================
- submit/runanchor-thumbnail.png        (title card, 3:2)
- submit/gallery-scoreboard.png         (measured result, video frame)
- submit/gallery-receipt.png            (receipt fields, video frame)
- submit/gallery-architecture.png       (under-the-hood, video frame)

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
