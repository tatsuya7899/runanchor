# 実装レビュー結果(敵対的) — 2026-09-29

- **レビュー経路**: `subagent_explore`(plannerのモデルクォータ枯渇のため、規約改訂後の第1代替=Devin内read-onlyプロファイル。コンテキスト非共有)
- **対象**: app/runanchor/*.py + app/tests/*(コミット `595120e` 時点)・bd/SPEC-runanchor_requirements.md / _design.md・researchノート突合
- **総合判定**: **不合格(P0あり)** — P0-1は「-D再実行でresult_image_uuidが返る」未検証前提。前提が実測で正しければ「修正要(P1群のみ)」に格下げ

## 指摘サマリ

### P0(要件破綻)
- **P0-1**: `-D`再実行で`result_image_uuid`が返る前提が無検証のままverify比較軸に入っている。返らなければ「一番検証したい採用候補ほど必ずmismatch」でverify空転。→ **#0実測必須項目へ昇格**(research §4)。退路=比較軸を落とすor再実行を非disposable化を設計追補に記録

### P1(全8件修正済み)
- P1-1 cwdがargvに載らず記録のみ → `sh -c "cd <cwd> && <cmd>"`ラップで実効化
- P1-2 _parse_opのフィールド仮定がmodels.py実資料と矛盾 → 準拠へ更新+欠落時warnings記録
- P1-3 `op show HEAD`誤アンカー → `run -o json`でuuid直取り、フォールバックはanchor_source="head"で区別
- P1-4 実行インフラ失敗でreceipt喪失 → DRIVER_ERROR縮退レコード経路(FR-1厳密化)
- P1-5 厳密SHA比較で非決定出力が偽不一致化+mismatch終端 → 揮発トークン正規化+mismatch→adopted/rejected回復遷移
- P1-6 --fileマウントが記録・再現されない → Receipt.files追加+verify再現
- P1-7 jsonl破損で台帳全滅 → 壊行スキップ+corrupt_lines()可視化+チェーンハッシュ(tamper検出)+fsync
- P1-8 秘密混入経路(command/tailが台帳へ) → 発行時スクラブ(台帳は公開物になりうるため)

### P2(選択適用)
- 採用: verify run失敗→unverifiable / verifyセッション分離 / DemoDriver強制demo印 / empty command→DriverError / stderr_tail追加 / append時pending+一意検証 / history()履歴API / from_dict前方互換 / events()型ガード
- 見送り(MLP記録): 並行decideロック(単一プロセス前提)、台帳自体の改竄耐性→チェーンハッシュで対応、status比較(語彙揺れリスク)

### テストの盲点(対応済み)
- 破損/部分行jsonl・チェーン整合・タイミング揺れ偽不一致・verify→decide統合・DRIVER_ERROR経路・files再現・S2フィールド存在 の各テストを追加(84テストGreen)

## 評価

レビューの正しさ: P0-1は製品の存立を左右する前提の炙り出しとして最も価値が高い。P1群は「証拠の誤記述」「誤アンカー」「証拠喪失」系で、いずれもツールの存在意義(証拠性)を静かに損なう性質 — 出る前に潰せてよかった。

残るリスクは全て「実プロバイダ応答の実測」に集中しており、ベータ承認待ちの現在はコード側でできる上限まで潰した状態。
