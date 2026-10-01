# SESSION-HANDOFF — runanchor 全記録(2026-09-29時点)

> **English summary**: Session handoff log as of 2026-09-29 — everything
> completed offline while the Sandboxes beta approval was pending: full
> implementation, three adversarial review rounds, the 35-item corpus, and
> submission text. The only blocker at that point was the beta-approval
> email (later resolved; see eval/bench-*.md for the live results).

**1行**: Sandboxesベータ承認待ちのまま、オフラインで組める全実装・敵対的レビュー3ラウンド・コーパス35件・提出物文面・棚卸し修正を完了。残ブロッカーはベータ承認メールのみ。

---

## 現在地(物理証拠)

- HEAD: `0b0d643`(main・clean)
- テスト: **97本全Green**(`./scripts/verify` exit 0)
- `python3 scripts/ready.py`: **17/18 PASS・NOT READY** — 唯一のFAILは「計量値が`_pending_`」= ライブ計量未実施。設計どおりの正直なブロック(嘘の数字では提出できない)
- コーパス: **35件(seeded 24 / clean 11)**・追跡ファイル144件・`scripts/build_corpus.py`で**byte同一再生成を実測確認**(全ファイルshasum diff一致)
- 推論API実測済み: `api.tokenfactory.nebius.com`・`nvidia/Nemotron-3_5-Lightning`動作・最小呼出し≒$0.000004・**seedは受理されるが非決定的**(同一プロンプト2回で応答不一致を実測)
- Sandboxes(ConTree): クローズドベータ申請済み・**ベータ期間中は実行がクレジット消費しない**(コンソール表示確認)

## 提出物チェックリストの状態(playbook §11照合)

| 項目 | 状態 |
|---|---|
| 冒頭headline実測値 | ⏳ `_pending_`(唯一の未完了・ベータ待ち) |
| Key findings/条件行列 | ✅ `eval/BASELINE.md`(条件行列+計量計画+層分離) |
| アーキテクチャ図 | ✅ `docs/architecture.svg` |
| サービス×利用箇所×証拠の表 | ✅ README「Token Factory / Nebius usage depth」節(live-verified列で単体テストと実API確認を分離) |
| コスト実測内訳 | ⏳ 推論$0.000004/callのみ実測・run単位は計量待ち |
| 「やっていないこと」明示 | ✅ README/descriptionのhonest limits節 |
| 再現手順 | ✅ demo・verify.py・build_corpus.py(byte同一実測済み) |
| 計量器自身のレビュー | ✅ 第3ラウンドで実施(漏洩+未配線を検出修正) |
| 意外な発見/負の発見 | ⏳ 要ライブ計量(最有力候補: judge単独での取りこぼし率) |
| 動画の証拠シーン設計 | ✅ `submit/demo-script.md`+`narration-claims.md`(主張台帳) |
| 提出アーティファクト内包 | ✅ submit/5点全てrepo内 |
| ライセンスバッジ | ✅ 2026-09-29棚卸しで追加 |

## 時系列の全記録

### Phase A: 事業設計(9/27〜28・過去セッション)
- `IDEA-runanchor_premises.md`(前提整理・Gate 0: 初回「追補」→6件潰し→承認) — skill側v1.3の由来実走
- `IDEA-runanchor_dtf.md`(構造破壊・Gate 1「追補」→バイアス表追補・致命的2件+重大15件受理)
- `SPEC-runanchor_requirements.md`(FR-1〜11・受入9件・スコープ外8件)/`_design`/`_tasks`
- 改名: agent-receipt → runanchor(npm/GitHubで4重占有のため)

### Phase B: プロバイダ調査・実測(9/29)
- `contree auth`済み(トークンは`~/.config/contree/auth.ini`・メモは削除指示済み)
- Sandboxes: project ID `aiproject-e00s4xh4qzf33mak7z`でベータ申請送信
- 推論API実測(コミット`fa8ea51`→`research/contree-notes_runanchor_20260929.md`): OpenAI互換・同一キー・Nemotron 4種・Lightning最安$0.06/$0.24・**seed非決定性の実測発見**・SWE-bench環境プリロード確認
- FR-11追補(計量の第三者再現可能性)コミット`ec29a9d`

### Phase C: TDD実装(9/29・承認待ち中に全非依存層)
- `75c1a6c` #1 receipt+ledger(14テスト) → `ffc94e4` #2-4 driver seam+gate+verifier(34) → `595120e` #5-11 demo+agent_loop+judge+cli+corpus骨格+bench+verify.py(67)

### Phase D: 敵対的レビュー3ラウンド(9/29)
- **R1**(`98f79ac`・84テスト): 初回判定「不合格」— 致命的1件(`-D`のresult_image_uuid前提未検証)+重大8件(cwd未実行記録・HEAD誤アンカー・台帳破損全滅・秘密混入・指紋偽不一致等)を全修正。台帳にハッシュチェーン追加
- **R2**(`b28ec11`・94テスト): 修正自体が生んだ重大3件(縮退レコードの偽不一致化・uuid喪失・warningsスクラブ迂回)+実質P2(verify証跡の台帳記録・demo/live混交ブロック・seed配線・例外捕捉)
- **R3**(`09ef16e`+`5501de9`・97テスト): **計量ハーネスの根本欠陥2件** — ①ラベル漏洩(benchが`task=slug`を渡しjudgeに"seeded-"が見える=採点循環)②タスク/seed未配線(plannerにタスク不達・seed/未マウント=何も測らない)。自走検証`check_corpus.py`でclean2件の緑開始偽装+`seeded-order-state`罠の機構不成立も発見修正(実機で1回目緑→2回目赤を確認)

### Phase E: 提出物・ゲート(9/29)
- `bf764c8`+`d35f7d1`: corpus35件・README・submit/3点・architecture.svg・`ready.py`・`record_demo.py`
- `d848cdc`: usage depth表追加(プリミティブ×利用箇所×証拠×live-verified)
- `b9539c3`: ready.py秘密スキャン誤爆修正(実パターン再利用+埋め込み語/プレースホルダ/識別子代入の除外3形態)

### Phase F: 勝者比較評価(9/29)
- 結論: **器は勝者水準以上・勝者たる証拠(headline実測値)だけが外部依存で欠けている**。再現性3層化・台帳ハッシュチェーン・計量器レビュー実績は勝者に無い資産。不足は実測値・コスト内訳・意外な発見・ライブ実演映像 — 全てベータ承認で解く
- ROI構造の確認: トークン代$0.01/runに対し防ぐ損失は桁違い・真のコストは人間レビュー時間(計量モードがその回答)・Nebius側は「GPU基盤の入口商品」モデルで整合

### Phase G: 棚卸し・学び還元(9/29・本記録作成と同時)
- 監査で検出した漏れ5件を修正(`e6e5e7b`+`0b0d643`): ライセンスバッジ欠落/`form-answers.md`未作成/bd5件のslug規約違反/description.mdテスト数陳腐化(94→97)/ready.pyのform-answers未検査(18項目化)
- コーパスbyte同一再生成を実測確認
- **学び還元**(親repo`6033503`+skill側):
  - `_ops/lessons/LESSON-20260929-004`: 秘密スキャンは実パターン+除外3形態(卒業①コード化済み)
  - `LESSON-20260929-005`: 計量器自身を敵対レビュー+実機確認の対象に(卒業②playbook §11計量節へ追記済み)
  - business-design skill **v1.4**: phase0「外部依存の物理検証」に依存3分類(即時検証可/安価実測可/承認待ち)+承認待ちへの縮退経路・IF分離要求+前提の退路記述を追加

## ブロッカーと再開手順

**唯一のブロッカー: Nebius Sandboxesベータ承認メール**(申請済み・時期不明)。

### 承認到着後(#0・技術検証第1号)
1. `contree images`が見えるか確認(権限付与の合図)
2. 最小`contree run -o json` → operation UUID取得
3. `contree op show <uuid>` → フィールド実測・`_parse_op`対応表確定
4. **`contree run -D`が`result_image_uuid`を返すか確認** — 返さなければverifyの`result_image_present`比較軸を除去する退路を実行(設計書追補記録済み)
5. stdout/stderr/exit code/リソース計量の実スキーマを`research/`へ記録

### その後の完了までの道
6. ベンチ実測(感度・特異度・コスト・所要時間) → `eval/bench-YYYYMMDD.md`に行レベル記録
7. README/description/form-answersの`_pending_`を実測値で置換 → `ready.py`全緑
8. `record_demo.py`で録画 → `demo-script.md`+`narration-claims.md`と照合
9. 外部公開(GitHub公開・YouTube・Devpost送信)は**人間承認必須**

## 主要ファイル地図

- `app/runanchor/`: receipt / ledger / contree_driver / gate / verifier / agent_loop / judge / bench / cli / demo / sanitize
- `app/corpus/`(35件・144ファイル)・生成=`scripts/build_corpus.py`・実機検証=`scripts/check_corpus.py`
- `app/fixtures/demo/`(ops.jsonl・events.json・verify/ops.jsonl)
- 提出物: `README.md`・`submit/`(description・feedback・demo-script・narration-claims・form-answers)・`docs/architecture.svg`・`LICENSE`(MIT)
- ゲート: `scripts/verify`/`verify.py`(97テスト)・`scripts/ready.py`(18項目)・`scripts/record_demo.py`
- 設計・レビュー記録: `bd/SPEC-runanchor_*`・`bd/IDEA-runanchor_*`・`bd/review-*_runanchor_20260929.md`
- 調査: `research/contree-notes_runanchor_20260929.md`・計量計画: `eval/BASELINE.md`

## 委任経緯の記録

builder週次クォータ枯渇(2026-09-29確認)のため、`bd/SPEC-runanchor_tasks.md`注記のフォールバック規約に従い監督が直接実装(型B委任不能・同一検証手順で実施)。

## 製品の一言メタファー(動画・説明に使える)

「**改竄不能なgit serverに、実行のたびに強制コミットされる仕組み**」 — operation記録=プロバイダ側のコミットメタデータ、result image=コミット内容。エージェントには書き込めない台帳だからこそ証拠になる。
