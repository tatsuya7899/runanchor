# Narration claims — runanchor

動画のナレーション・字幕・README/説明文の**定量的主張・能力主張は全てこの表に1行を持つ**。表に無い主張は書かない。

| # | 主張(台詞・字幕・説明文の原文) | 種別 | 根拠(ファイル/テスト/実演の位置) | 状態 |
|---|---|---|---|---|
| 1 | "The agent said 'all tests pass.' Do you believe it?" | 能力 | 撒き種runの実演(嘘つきreceiptの実在) | 未作成 |
| 2 | "Every run gets a receipt — anchored to the provider's own record" | 能力 | `runanchor run`実演 + receipt内のoperation UUID/image ID | 未作成 |
| 3 | "Not a self-report. A verifiable record" | 能力 | receiptのフィールド実演 | 未作成 |
| 4 | "A false claim can't survive re-execution" | 能力 | `runanchor verify`のimage fork再実行実演 | 未作成 |
| 5 | "We measured the gate itself" | 定量 | `eval/bench-*.md`の感度/特異度表 | 未作成 |
| 6 | "Open source. Reproduce in 60 seconds" | 能力 | READMEのReproduce節・`--demo`モード実測 | 未作成 |

- 種別: 定量(数値を含む)/ 能力(できる・自動で・常時 等)/ 比較(他より)
- 状態: verified(根拠が今も通る)/ 実演済み(動画内で実演)/ ⚠格下げ(断定→設計表現に変えた)/ 未作成
- 根拠が動くもの(live URL等)は書かないか境界を明記する
