# demo-script — runanchor(3分以内・英語テロップ型)

> 動画台本。タイムラインは撮影後に実測で埋める。主張は全て `submit/narration-claims.md` の表に対応させる(表に無い主張は入れない)。

## 構成(案)

| 時間 | 画面 | テロップ(英語) | 対応する主張 |
|---|---|---|---|
| 0:00-0:15 | 問題提示 | "The agent said 'all tests pass.' Do you believe it?" | narration-claims #1 |
| 0:15-0:45 | `runanchor run` 実演 — agentがsandbox内でコードを書き・走らせ・赤→緑へ自律1ループ | "Every run gets a receipt — anchored to the provider's own record" | #2 |
| 0:45-1:30 | receiptの中身: diff hash・テストログ・operation UUID・image ID | "Not a self-report. A verifiable record" | #3 |
| 1:30-2:15 | `runanchor verify` — image fork→再実行→比較 / 嘘つきrunの暴き(クライマックス) | "A false claim can't survive re-execution" | #4 |
| 2:15-2:45 | 関所: approve/reject + 計量モード(撒き種コーパスに対する感度/特異度) | "We measured the gate itself" | #5 |
| 2:45-3:00 | まとめ・repo案内 | "Open source. Reproduce in 60 seconds" | #6 |

## 収録メモ

- 審査員経路はライブAPI非依存にする(`--demo`モード) — Beta安定性×審査12月のリスク回避
- ナレーションはテロップ(字幕)型。音声ナレーション必須ではない
- 「やっていないこと」も1テロップ入れる(ライブ依存の制限など)
