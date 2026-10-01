# Narration claims — runanchor

Every quantitative or capability claim made in the video narration,
captions, and README/description text maps to exactly one row of this
table. Do not write claims that have no row here.

| # | Claim (as spoken / captioned) | Type | Evidence (file / test / demo location) | Status |
|---|---|---|---|---|
| 1 | "The agent said 'all tests pass.' Do you believe it?" | capability | seeded-run demo (a lying receipt exists) | verified |
| 2 | "Every run gets a receipt — anchored to the provider's own record" | capability | `runanchor run` demo + the operation UUID / image IDs inside the receipt | verified |
| 3 | "Not a self-report. A verifiable record" | capability | receipt fields demonstrated | verified |
| 4 | "A false claim can't survive re-execution" | capability | `runanchor verify` replay demo (fork start image → rerun → fingerprint compare) | verified |
| 4b | "And a green-but-wrong answer can't survive tests it never saw" | capability | oracle demo (fork result image → hidden tests mounted at a unique path outside the workspace, run under isolated `python3 -I -S`) | verified |
| 5 | "We measured the gate itself — evidence review alone vs the full gate" | quantitative | two-layer matrix in `eval/bench-20261001-v4.md` (evidence-only / gate, n=54) | verified |
| 6 | "Open source. Reproduce it yourself" | capability | README Reproduce section, `runanchor demo`, `scripts/bench_live_runanchor.py` | verified |
| 7 | "The ledger keeps the failures too" | capability | `runanchor check` hash-chain verification; rejected/unresolved rows demonstrated | verified |

- Type: quantitative (contains numbers) / capability (can, automatic, always…) / comparison (better than…)
- Status: verified (evidence still passes) / demonstrated (performed on screen) / downgraded (assertion rewritten as design wording) / not-yet
- Claims whose evidence can move (live URLs etc.) are either omitted or carry an explicit boundary note
