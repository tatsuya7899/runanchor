# Narration claims — runanchor

動画のナレーション・字幕・README/説明文の**定量的主張・能力主張は全てこの表に1行を持つ**。表に無い主張は書かない。

| # | 主張(台詞・字幕・説明文の原文) | 種別 | 根拠(ファイル/テスト/実演の位置) | 状態 |
|---|---|---|---|---|
| 1 | "The agent said 'all tests pass.' Do you believe it?" | 能力 | 撒き種runの実演(嘘つきreceiptの実在) | verified |
| 2 | "Every run gets a receipt — anchored to the provider's own record" | 能力 | `runanchor run`実演 + receipt内のoperation UUID/image ID | verified |
| 3 | "Not a self-report. A verifiable record" | 能力 | receiptのフィールド実演 | verified |
| 4 | "A false claim can't survive re-execution" | 能力 | `runanchor verify`のreplay実演(start image fork→再実行→fingerprint比較) | verified |
| 4b | "And a green-but-wrong answer can't survive tests it never saw" | 能力 | oracle実演(result image fork→隠しテストをworkspace外の独特pathにマウント・`python3 -I -S`隔離runnerで実行) | verified |
| 5 | "We measured the gate itself — evidence review alone vs the full gate" | 定量 | `eval/bench-20260930-v3.md`の2層行列(evidence-only / gate) | verified |
| 6 | "Open source. Reproduce it yourself" | 能力 | READMEのReproduce節・`runanchor demo`・`scripts/bench_live_runanchor.py` | verified |
| 7 | "The ledger keeps the failures too" | 能力 | `runanchor check`のhash chain検証・rejected/unresolved行の実演 | verified |

- 種別: 定量(数値を含む)/ 能力(できる・自動で・常時 等)/ 比較(他より)
- 状態: verified(根拠が今も通る)/ 実演済み(動画内で実演)/ ⚠格下げ(断定→設計表現に変えた)/ 未作成
- 根拠が動くもの(live URL等)は書かないか境界を明記する
