# narration text — runanchor demo video (7 scenes · total ≈ 2:03)

動画音声の収録・生成用原稿。各行は `submit/narration-claims.md` のverified行に対応
(表に無い主張は足さない)。シーン単位で1ファイルずつ音声化すると、そのまま
レンダラ(`scripts/render_demo_video_runanchor.py --audio-dir <dir>`)に差し込める。

収録の指針: 各シーンの尺は「音声長+1.2s」で自動決まる。短い=テンポ良くなる。
下げないこと: 句読点の間(ピリオド後は一拍)。TTSなら en-US 自然声、rate ~178wpm が映像と合う。

---

## Scene 1 — Title card(最小7.0s / 現TTS 8.9s)

```
AI agents say: "done, tests pass." Who checks that?
CI checks artifacts. Nobody checks the agent's report.
runanchor does.
```
(claims表 #1)

## Scene 2 — `runanchor demo` 実演(最小20.0s / 現TTS 12.8s)

```
Every run gets a receipt, anchored to the provider's own execution
record — not the agent's self-report. Three runs: a real failure,
a false success claim — rejected — and a verified fix, adopted.
```
(claims表 #2)

## Scene 3 — list + receipt show(最小22.0s / 現TTS 10.5s)

```
Not a self-report. A verifiable record. Provider-issued operation
and image IDs, stream fingerprints, and the decision:
adopted after replay verifies.
```
(claims表 #3 + #4)

## Scene 4 — 2軸検証の図解(最小24.0s / 現TTS 17.1s)

```
Two independent checks. Replay forks the recorded start image and
reruns the command — a reported-but-not-run claim cannot survive
re-execution. The hidden oracle runs tests the agent never saw,
mounted outside its workspace under an isolated interpreter —
so green-but-wrong cannot survive either.
```
(claims表 #4 + #4b)

## Scene 5 — 実測スコアボード(山・最小24.0s / 現TTS 18.4s)

```
We measured the gate itself, on live Nebius sandboxes. Reading
evidence alone, the judge caught seven of eleven defective runs.
With replay and the hidden oracle — all eleven, while passing
forty-two of forty-three good runs. The corpus, the judge prompt,
and the ledger are in the repo: check our numbers, not our claims.
```
(claims表 #5 + #6)

## Scene 6 — アーキテクチャ(最小16.0s / 現TTS 12.5s)

```
Under the hood: ConTree sandbox operations anchor every receipt.
Nemotron plans the agent loop; Nemotron judges the evidence.
Everything lands on an append-only, hash-chained ledger —
even the failures.
```
(claims表 #7)

## Scene 7 — クローズ(最小6.5s / 現TTS 6.2s)

```
runanchor. MIT licensed, offline demo in the repo.
Check our numbers, not our claims.
```
(claims表 #6)

---

## 音声差し替え手順(Owner)

1. シーンごとに1ファイル: `narration-1.wav` … `narration-7.wav`
   (wav/mp3/m4a/aiff 可。ファイル名の数字がシーン番号)
2. 例: あるディレクトリに置いて `python3 scripts/render_demo_video_runanchor.py
   --workdir /tmp/ra-video --audio-dir <そのdir> --out submit/runanchor-demo.mp4`
3. 尺は音声長に自動追従するので再編集不要。欠落した番号はTTSにフォールバック。

再生成後は `submit/runanchor-demo.mp4` を差し替えてコミット。
