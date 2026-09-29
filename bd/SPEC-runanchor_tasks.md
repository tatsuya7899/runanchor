# runanchor — タスク

**前提**: SPEC-runanchor_design.md(セルフレビュー通過・独立レビューはクォータ復帰後に再実施予定)
**日付**: 2026-09-29

## 実装順

| # | タスク | 種別 | 委任先 | 投資量 | 依存 | 完了判定 |
|---|---|---|---|---|---|---|
| 0 | **技術検証第1号**(人間): APIキー発行→`contree auth`→最小`contree run`で単価計測+research §4潰し | 探索型 | Owner人間(+監督補助) | 軽量 | メンテ明け(9/30 02:00 JST) | operation UUID取得・単価判明・未確認リスト更新 |
| 1 | `receipt.py`+`ledger.py`: スキーマ・台帳・状態機械+テスト(S1/S3/S4のRed→Green) | 安定型 | builder | 標準 | — | 該当テストGreen |
| 2 | `contree_driver.py`: DriverIF+ContreeDriver(CLI subprocess)+DemoDriver(fixture) | 安定型 | builder | 標準 | —(実接続は0後) | IFモック結合テストGreen |
| 3 | `gate.py`: pending/approve/reject+理由必須+削除不可 | 安定型 | builder | 標準 | 1 | テストGreen(S3/S4) |
| 4 | `verifier.py`: 個別receipt再実行比較(フェイクdriverで一致/不一致両経路) | 安定型 | builder | 標準 | 2 | テストGreen(S5/S6) |
| 5 | `demo.py`+`app/fixtures/`: 記録済みops/receipt fixture・撒き種repo snapshot | 安定型 | builder | 標準 | 1,2 | デモデータ読込テストGreen |
| 6 | `agent_loop.py`: Nemotron駆動ループ+停止条件(demoではfixture再生可能に) | 安定型 | builder | 重め | 2,5 | 系列receipt生成テストGreen(S9) |
| 7 | `judge.py`: Nemotronレビュアー(証拠のみ入力・構造化採否)+サニタイズ | 安定型 | builder | 標準 | 3 | フェイクjudge結合テストGreen(S8の機械部) |
| 8 | `cli.py`: run/list/show/approve/reject/verify/bench配線+`--demo` | 安定型 | builder | 標準 | 3,4,5,6 | E2E(デモ・ネットワーク遮断)Green(S7) |
| 9 | `app/corpus/`撒き種タスク: seeded≈24+clean≈11(生成器+手作り・潜る系主軸) | 安定型 | builder | 重め | — | label整合チェック+既存テスト緑確認 |
| 10 | `bench.py`: コーパスランナー+混同行列+感度/特異度レポート | 安定型 | builder | 標準 | 6,7,9 | ミニコーパス(n=4+2)で行列出力 |
| 11 | `scripts/verify`: オフライン全量テスト+ライブ系フラグ分離 | 安定型 | builder | 軽量 | 1-10 | `./scripts/verify` exit 0 |
| 12 | README(EN)書き直し+LICENSE+提出説明文+アーキテクチャ図 | — | editor | 標準 | 実装後 | shipping-reviewer(外部公開前・必須) |
| 13 | デモ動画(≤3分・音声説明)制作パイプライン | — | editor/builder | 標準 | 11 | 提出物形式適合 |
| 14 | 計量本実行(bench・残クレジット見積→承認→実行)+README冒頭数値 | — | 監督+承認 | クレジット | 0,10 | 感度/特異度実測掲載 |
| 15 | 提出パッケージ(GitHub公開化・Devpostフォーム・test build) | — | shipping-reviewer→人間承認 | — | 12,14 | 即時検収(例外なし) |

## 注記

- **1タスク=1ファイル編集→検証**(R2)。同種修正の一括置換禁止
- **並列候補**: 一発で通る見込みが薄いのは #6(ループの振る舞い)と #9(コーパスの質)。それぞれテンプレG(同一プロンプト3並列)を検討
- **直列固定**: #0は全ての前件。#6→#10・#9→#10は直列。#1-#5は互いに依存が薄く並列可(ただし委任先クォータ次第)
- **ライブ系テスト**(実contree/実Nemotron呼出し)は`--live`フラグで分離し、既定の`./scripts/verify`には含めない(クレジット消費・再現性のため)
- **レビューゲート**: 非自明な実装(#2,#6,#9,#10)は完了報告前にPlan agent敵対的レビュー。クォータ枯渇が続く場合は規約フォールバック(分離セルフレビュー)で代替し、その旨を記録に明記
- **サブエージェントクォータ**: 週次クォータ枯渇が確認済み(2026-09-29)。builder委任が不能な場合、監督が同じ検証手順(1ファイル→テスト)で直接実装し、理由を報告に明記する(agentic-hackathon-vol5 AGENTSの先例)

## 差し戻し

- 同一指摘の往復は2回まで。3ラウンドを超えたら振動とみなし人間裁定(`AI_CROSS_REVIEW_STRATEGY_20260831.md` §4)
