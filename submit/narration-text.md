# narration text — runanchor demo video (7 scenes · total ≈ 2:04)

Recording/generation script for the video voiceover. Each section maps to
a verified row in `submit/narration-claims.md` (no claims outside the
table). Record one file per scene and the renderer picks them up via
`scripts/render_demo_video_runanchor.py --audio-dir <dir>`.

Recording guide: each scene's length auto-follows audio length + 1.2s —
shorter is tighter. Keep the pauses at punctuation (one beat after a
period). For TTS, an en-US natural voice at ~178 wpm matches the pacing.

---

## Scene 1 — Title card (min 7.0s)

```
AI agents say: "done, tests pass." Who checks that?
CI checks artifacts. Nobody checks the agent's report.
runanchor does.
```
(claims table #1)

## Scene 2 — `runanchor demo` live demo (min 20.0s)

```
Every run gets a receipt, anchored to the provider's own execution
record — not the agent's self-report. Three runs: a real failure,
a false success claim — rejected — and a verified fix, adopted.
```
(claims table #2)

## Scene 3 — list + receipt show (min 22.0s)

```
Not a self-report. A verifiable record. Provider-issued operation
and image IDs, stream fingerprints, and the decision:
adopted after replay verifies.
```
(claims table #3 + #4)

## Scene 4 — two-axis verification diagram (min 24.0s)

```
Two independent checks. Replay forks the recorded start image and
reruns the command — a reported-but-not-run claim cannot survive
re-execution. The hidden oracle runs tests the agent never saw,
mounted outside its workspace under an isolated interpreter —
so green-but-wrong cannot survive either.
```
(claims table #4 + #4b)

## Scene 5 — measured scoreboard (climax · min 24.0s)

```
We measured the gate itself, on live Nebius sandboxes. Reading
evidence alone, the judge caught seven of eleven defective runs.
With replay and the hidden oracle — all eleven, while passing
forty-two of forty-three good runs. The corpus, the judge prompt,
and the ledger are in the repo: check our numbers, not our claims.
```
(claims table #5 + #6)

## Scene 6 — architecture (min 16.0s)

```
Under the hood: ConTree sandbox operations anchor every receipt.
Nemotron plans the agent loop; Nemotron judges the evidence.
Everything lands on an append-only, hash-chained ledger —
even the failures.
```
(claims table #7)

## Scene 7 — close (min 6.5s)

```
runanchor. MIT licensed, offline demo in the repo.
Check our numbers, not our claims.
```
(claims table #6)

---

## Replacing audio (owner)

1. One file per scene: `narration-1.mp3` … `narration-7.mp3`
   (wav/mp3/m4a/aiff all work; the number in the filename is the scene)
2. Example: put them in a directory and run
   `python3 scripts/render_demo_video_runanchor.py
   --workdir /tmp/ra-video --audio-dir <that dir> --out submit/runanchor-demo.mp4`
   (requires pillow + numpy, e.g. `uv run --with pillow --with numpy`)
3. Scene length follows the audio automatically — no re-editing needed.
   Missing numbers fall back to TTS.

After regenerating, replace `submit/runanchor-demo.mp4` and commit.
