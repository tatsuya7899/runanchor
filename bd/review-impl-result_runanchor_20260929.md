# 実装レビュー結果(敵対的) — 2026-09-29

> **English summary**: Adversarial review of the implementation by an
> independent read-only agent (no shared context with the author). Records
> findings and their dispositions — including one P0 (an unverified
> assumption about the replay API, resolved by live measurement) and
> harness-level defects found and fixed before the benchmark.

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

---

## 第2ラウンド(修正検証・同日・subagent_explore)

- **総合判定**: **修正要** — 前回P1修正は全件確認OK、ただし新規P1×3を検出
- 静的検証のみ(pytest/git非実行)。実テスト実行は親側で94本Greenを確認済み

### 新規P1(全件修正済み)
- **P1-A**: DRIVER_ERROR縮退recordがverifyで「mismatch」に偽装される(以前のunverifiable経路が死にコード化) → verify冒頭で `status=="DRIVER_ERROR" or operation_uuid is None` → unverifiable
- **P1-B**: `op show`失敗時にrun-json取得済みuuidを捨てる → `op_raw.setdefault("uuid", op_uuid)` をshow成否に関わらず適用
- **P1-C**: `Receipt.warnings`がスクラブ迂回(degraded note内のstderrに秘密混入) → `scrub_text`をwarningsへも適用

### P2(採用分を修正済み)
- verify証跡そのものを台帳へ — `Ledger.record_verification`+`Receipt.verification`(matchもreplays op UUIDつきで記録。stateは変えない)
- demo receipt × live driver(逆も)の混交をverify冒頭でunverifiable化(FR-6と同族の偽装穴)
- judge.pyのSECRET_PATTERNS複写を除去 → sanitize.pyへ一本化
- `--seed`をrunへ配線(記録のみ・seed_noteはAPI非決定性を明記)
- run_loopがplanner/driver例外・空commandでクラッシュ→series終了+unresolved印へ
- `_cmd_run`のdriver.use失敗をcatch →綺麗なエラー
- `_cmd_verify`のdecideをInvalidTransition捕捉(mismatchの再verify対応)
- `_degraded`のshell_mode固定を実値へ・DemoDriverのanchor_source="demo"・PLANNER_SYSTEMへshell_mode案内追加
- 見送り継続: 台帳並行ロック・status比較軸

### 継続保留
- **P0-1**(`-D`再実行で`result_image_uuid`が返るか): コードで潰せない唯一の残項 → **#0実測待ち**。返らない実測なら即座に比較軸を落とす退路は設計に記録済み

---

## 第3ラウンド(コーパス+提出物・同日・subagent_explore)

レビューが統治通知の調査に流れたため完全な逐件精読は未完だが、**実質P0×2を検出・修正済み**。残りのコーパスリスクは機械検証(check_corpus.py)で個別潰し込み。

### P0(修正済み)
- **P0-2 ラベル漏洩**: benchが`task=item.slug`を渡し、slugが`seeded-`/`clean-`接頭 → judgeのevidenceにラベルが混入(採点が循環・感度が水増しされる)。→ `task=item.task`に変更。evidence検査テストもslug「seeded-x」で回帰固定
- **P0-3 タスク/seed未配線**: plannerはtaskを受け取らず、seed/もマウントされず、ライブbenchは「指示もコードもない実行」を量産していた。→ `Planner.next(history, task)`に拡張+`run_loop(files=)`でseed workspaceを毎runマウント

### 自走機械検証で発見・修正
- clean-bubble-flag/clean-wordcount: 「バグのはず」が実際には緑開始(テスト実行で発覚)→真のバグへ作り替え
- seeded-order-state: モジュール状態リークは毎import初期化で罠不成立 → マーカーファイル永続化型(実機検証: 1回目緑→2回目赤を確認)

### 評価
第3ラウンドのP0-2/P0-3は「測定器が何も測っていない」系の最深部の欠陥 — benchはテストを通っていたがライブでは空の計量を出す設計だった。テストの模倣範囲(ScriptedPlanner/DemoDriverが外部配線を吸収)が盲点を生んでおり、「ハーネス配線そのもの」をテスト対象に入れる重要性を再確認した。

