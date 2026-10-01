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

============================================================
Additional info page — field by field
============================================================

Upload a File: (optional — skip)

Submitter Type *: Individual        (OWNER: adjust if different)
Organization Name: N/A
Submitter Country of Residence *: Japan
Canada province: N/A

Track *: Coding and Agentic Engineering

New or existing prior to August 26, 2026? *: New
  (runanchor was created 2026-09-29 — after the cutoff)

Public code repository URL *:
  https://github.com/tatsuya7899/runanchor
  (MIT LICENSE at repo root; README covers setup, the offline demo,
  Nemotron model usage, and where Token Factory was used)

Working demo URL:
  https://github.com/tatsuya7899/runanchor
  (no hosted app — `runanchor demo` runs fully offline with no
  credentials; the repository is the test build)

Which model(s) did you use, and why that size/variant? *:
  nvidia/nemotron-3-super-120b-a12b as the agent-loop planner, and
  nvidia/Nemotron-3_5-Lightning as the measurement judge. We chose
  different sizes deliberately: Lightning tended to loop on inspection
  commands instead of editing when used as a planner, so the multi-step
  agent loop runs on Super-120B; the judge is a one-shot structured
  verdict (adopt/reject + reason), where Lightning's speed and cost
  (~$0.06/$0.24 per 1M tokens) make per-run measurement realistic.

Rate Nemotron's output quality (1-10) *: 8
  What worked / fell short: as the judge, Lightning produced clean
  structured verdicts — 0/108 unparseable in the final benchmark after
  schema + retry. As a planner, Lightning under-performed (inspection
  loops, no edits); Super-120B honestly fixed 30 of 39 seeded tasks,
  judged by an executable oracle. Fell short: `seed` is accepted but not
  deterministic (3 identical calls, different outputs) — we record it as
  metadata only.

Fine-tune, prompt-engineer, or out of the box? *:
  Out of the box weights; prompt engineering on the judge side —
  structured verdict schema, retry-on-unparseable, and an explicit
  unparseable counter so a malformed verdict can never silently become a
  rejection. No fine-tuning; the corpus and judge prompt are committed so
  the measurement is reproducible.

Compare to other models for similar tasks *:
  Super-120B's agentic loops were competent — it completed honest fixes
  on the majority of seeded traps without hand-holding. Lightning is
  notably cheaper/faster than comparable judge-class models we have used,
  with two caveats: reasoning consumes the token budget (structured-output
  consumers must parse the last JSON object and budget headroom), and
  seed does not give determinism.

Nebius platform capabilities most valuable *:
  ConTree Sandboxes is the product's foundation — provider-issued
  operation UUIDs and image UUIDs are literally the anchor data runanchor
  receipts are built on, and image forking powers both verification axes
  (replay from the recorded start image; the hidden oracle mounts onto
  the produced result image). Token Factory's OpenAI-compatible endpoint
  shared the same API key as `contree auth` — zero extra auth plumbing.
  Preloaded SWE-bench-style images made benchmark tasks realistic.

Recommend Nemotron on Nebius (1-10) *: 8
  Why: the sandbox + inference combo let us build a verification tool
  that would be a mock elsewhere — real provider-side execution records.
  Held back from 10 by closed-beta friction (403s until the beta form
  cleared) and missing per-operation cost/token fields.

Rate inference experience vs other environments (1-10) *: 8
  OpenAI-compatible API + same key for CLI and inference meant our
  Python client was a drop-in; Lightning's per-token price made
  per-run judging inexpensive ($0.30 total project inference).
  Minus: non-deterministic seed, and `run -D` producing no result image
  was discoverable only by experiment.

Additional features/improvements *:
  Per-operation cost/token fields on `contree op show`; a published JSON
  schema for `op show`/`op events`; documentation up front that
  disposable runs produce no result image and that image UUIDs are not
  comparable across sessions; deterministic seeding (or a doc note that
  seed is advisory); beta-gate status stated in the docs, not only in the
  CLI error.

What do you most hope to see from the Nemotron team next? *:
  A mid-size variant tuned for agentic loops (edit-don't-inspect
  discipline) at Lightning-class cost, and deterministic sampling so
  receipt-anchored replays can be bit-compared end to end.

Did you use Tavily? *: No
Builders & Brews city: (blank / none — OWNER: select only if attending)

Checkboxes (both required *):
  [x] age of majority — tick
  [x] not employees of Promotion Entities — tick
