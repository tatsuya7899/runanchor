# 事業設計 前提整理: runanchor(エージェント作業の「検収書」関所) ※旧名agent-receipt・v1.2で改名
Created: 2026-09-29 / モード: 早駆け(Phase 0圧縮)
**v1.1(同日)**: Gate 0敵対的レビュー(判定「追補」・P1×6)を反映。外部前提は全件正確と検証済み(Token Factory Sandboxes実在・ConTree・7,000+ SWE環境プリロード・クレジット$50・締切・トラック文逐語一致)。修正点: CI差分の再記述・receipt外部アンカー・計量主体の定義・先行技術の引用・課金実測・エージェント最低品質。
**v1.2(同日)**: 課題フレーミングの敵対的レビュー(判定「追補・条件付き承認」)を反映。**改名 `agent-receipt` → `runanchor`**(npm/GitHubで4重占有を実測発見)。課題を3層構造に再定義・先行技術スイープにreceipt系クラスタ9件を追記・問題の質6属性を新設。詳細は末尾の追補2を参照。

## 確定スコープ(ハッカソン提出物としての前提)

- **Nebius × NVIDIA Global AI Hackathon・Coding and Agentic Engineering トラック**への提出物として設計する。個人開発・提供クレジット($50 Token Factory)内・締切 2026-10-30 10:00 PDT(約10/31 02:00 JST)
- トラック公式文: 「Build coding agents and developer tools: agents that write, run, and test code in **Token Factory Sandboxes**」
- ハード要件: 公開OSSリポ(README)・デモURL/テストビルド・3分以内の公開動画・**Nemotron等NVIDIAオープンソースモデルを Token Factory または Nebius AI Cloud で使用**
- 勝者の作法(精読済み): 価値はGUIでなく「リポが再現可能に証明する性質」。決定論コア+LLM縁・条件行列計量・天井値/ライブ分離・関所が撒き種を止める率の測定

## アイデア(1文)

コーディングエージェントがサンドボックスでコードを書き・走らせ・テストする**各実行に、検証可能な「検収書(receipt)」を発行する**。検収書には「何を変えたか(diff hash)・テストが実際に走ったか(ログの実在)・結果・コスト・根拠」を刻み、**人が承認して初めて「採用」になる**関所。

## ユーザーと痛み(仮説・Gate 2要検証)

- **ユーザー**: コーディングエージェント(Claude Code/Codex/Devin系)を実務で使う開発者。「ユーザーが見える」条件を満たす
- **痛み**: エージェントが「直しました」と言うが、テストが本当に走ったか・緑なのか・どこを触ったかを人が再確認しないとマージできない。「信頼するか自分で全部確認するか」の二択になっている
- **現状の代替**: 人がdiffとCIを目で見る(時間がかかる)/ 信用してマージ(撒き種バグを取り込む)
- **証拠強度**: 弱〜中。自分のStudio運用で毎日体験している痛み(N=1)。一般化はGate 2(開発者3人への聞き取り)で検証する

## USP(対抗軸・v1.1書き直し — 先行技術を踏まえた再定義)

**先行技術の実在(レビューで実調査済み)**: Pipelock/AARPは署名済みhash-chainの"action receipt"をOSS出荷済み、OpenHands SDKは承認ポリシー+audit trail、SWE-agentは`.traj`全記録+再実行、GitHub required reviews自体が承認状態機械。**「記録・承認・証跡はあるが、run単位の検証可能な検収書+採否状態機械+関所品質の計量の統合は無い」**(OpenHands issue #4259が同一概念の未実装feature request=ギャップ実在の公式証拠)

他の応募者は「賢くコードを書くエージェント」を作る。こちらは**書く側ではなく検収側**。残る差分3点:

1. **外部アンカーつき検収書**: receiptにConTree(Token Factory Sandboxes)発行のoperation UUID/image IDを埋め込み、プロバイダ側の実行記録をアンカーにする。`verify` = 「記録imageからfork→コマンド列再実行→結果比較」— receiptが自己申告でなく外部検証可能になる(verify-the-verifier)
2. **run単位の粒度**: PR/CIの承認は「変更一式」単位。こちらはエージェントの**各実行**(試行・失敗・reject済み作業も含む)を台帳化 — CIに現れない層
3. **関所品質の計量**: 撒き種コーパス(既知バグ入りタスク)で関所の感度/特異度を測る。README冒頭数値=この2値+コスト実測

## 計量の判定主体(v1.1で定義 — レビュー最深の指摘)

関所が人承認CLIだけでは計測不能(審査員クリック依存)。**判定主体を明確化**:

- **人間モード**(MVPのUI): 人がreceiptを見てapprove/reject — 製品としての姿
- **計量モード**(測定用): **Nemotronレビュアーがreceiptの証拠だけを見て採否判断**。正解ラベル(撒き種の有無)と突き合わせ、偽陰性(悪い成果物を通す)/偽陽性(良い成果物を止める)を測る → 非循環の条件行列が成立
- 撒き種数の補強(P2): 3種では二項CIが巨大 → ConTreeの7,000+プリロードSWE環境から条件行列の母数を確保する

## MVP(提出境界)

| 層 | 内容 |
|---|---|
| 実行 | `runanchor run "task"`: Nemotron(Token Factory)がSDK経由でConTreeサンドボックスを駆動(エージェント本体は外部・サンドボックスは実行場)。**「書く→走る→赤→直す→緑」の自律1ループ必須**(P1-6: エージェントが玩具だとTechnological Implementationで削られる) |
| 検収書 | 実行ごとに発行: diff hash・テストログ・exit code・コスト・モデル・シード・**ConTree operation UUID/image ID(外部アンカー)**。`runanchor verify <id>` = image fork→コマンド列再実行→結果比較 |
| 関所 | pending一覧→approve/reject CLI。rejected は理由付きで台帳に残る |
| デモ | `--demo` モード: 撒き種repo付属・**審査員経路はライブAPI非依存**(Beta安定性×審査窩12月のリスク回避・P2-3)。薄いWeb UIはMVP昇格検討(デモURL要件を兼ねる) |
| 計量 | 条件行列(バグ種別×エージェント挙動)×判定主体(人/機械)。BASELINE.mdに天井値、bench-reportに実測を分離 |

## MLP(lovable版・時間があれば)

- receipt の差分可視化ビューア(薄いWeb UI・`?demo=1` 対応)
- 連続実行のトレンド(同じタスクでreceiptがどう変わるか)
- 承認ポリシーの宣言的ルール(「テストカバレッジ低下は自動reject」等)

## 立ち位置(なぜあなたか)

Studio統治OSを毎日運用している人が、その個人版の関所を作る — 台帳(`agent_ledger.py`)・readinessゲート(`readiness.py`)・「証拠は実行で」の規律を製品に翻訳する構図。sagi-shieldの「関所+台帳+計量」DNAの開発領域版で、既存2作(水漏れ保険・防犯秘書)とドメインが被らない。

## 前提の最もリスクの高い仮定(v1.1更新)

1. **需要性**: 「エージェントの出力を検収したい」が他の開発者の実感として刺さるか(N=1の自分由来)。検証: Gate 2で開発者3人に「エージェントの出力をどう確認してる?」を聞く
2. **課金の実測(レビューで格上げ・CEO制約直結)**: Token Factory docsが矛盾(billing-new「カード必須」vs旧billing「プロモはカード無し可」)。Sandbox computeがクレジットを減らすか未回答のまま。**Gate 0の技術検証第1号 = クレジットのみでサインアップ→`contree run`→operation ID取得**(人間の操作が必要)
3. **ConTree(Beta)の安定性×審査タイミング**: 審査は12月。審査員経路をライブAPI非依存にする設計で回避(デモモード+fork検証は録画済みアンカーで代替可)
4. **命名衝突**: Pipelockの"action receipt"が先行占有 — "agent-receipt"は語として近い。READMEで差別化1行(「彼らはセキュリティ署名、こちらは検収+計量」)を入れる
5. **競合**: 調査済み(§USPの先行技術段落) — 差別化は「run単位検証可能検収書+関所計量の統合」に確定

## Gate 0追加確認(提出物型判定)

- 提出物型・ツール/検証型への適用: **適用**(ハッカソン提出物+開発者向けツール+検証が主題の三条件全てに該当)
- 既存機構との差分: 実名列挙済み(§USP — Pipelock/OpenHands/SWE-agent/GitHub reviews)
- 証拠の外部性: ConTree operation UUID/image IDを外部アンカーに採用(§USP-1)
- 計量の判定主体: 人間モード/計量モード(Nemotronレビュアー)を分離定義済み
- 先行技術スイープ: §USP実施済み。命名衝突=リスク#4に記録
- 外部依存の物理検証: 要求項目として固定(リスク#2・完了期限=実装着手前の技術検証第1号)
- 本体の最低品質: MVP表に「書く→走る→赤→直す→緑の自律1ループ必須」として固定済み

## Gate 0 への申し送り(v1.1)

- **Gate 0外部レビュー実施済み(2026-09-29・subagent)**: 初回判定「追補」→v1.1への6件反映を再監査 → **判定「承認」**(6件全解消確認済み)
- **設計段階への宿題3件**(再レビューで記録・ブロッカーではない): ①撒き種コーパスは「テスト赤」型でなく「既存テスト緑だが潜る/ログ偽装」型に重心を置く(感度100%退化の回避) ②MLP3件のカット順をtasks段階で規定 ③「人条件は探索的・MSCは機械条件のみ」と設計時に明記
- **次**: **人間作業が必要な技術検証**(Token Factoryクレジットのみサインアップ→`contree run`→operation ID取得) → その後 feature-spec 3段階要件(requirements→design→tasks)へ
- MSCの帯: トラックWinner以上 — 判定基準は「関所が撒き種を止める率(感度/特異度・判定主体=機械)」の測定結果が出るか

---

## 追補2(2026-09-29・課題フレーミングの敵対的レビュー「追補・条件付き承認」を反映)

レビュー全文は当セッションのレビュアー報告に記録。本文(上記Gate 0承認済み部分)は追補方式のため改変せず、本節で上書きする。

### 改名: `agent-receipt` → `runanchor`

- **理由**: `agent-receipt`がnpm(`RLASAF12/agent-receipt`・`npx`でインストール可)とGitHubで4重占有。同名ツールが既に「AIの完了申告をreceipt化」ピッチで出ているため、名称での差別化が成立しない
- **新名の意味**: 「実行(run)を外部記録に錨(anchor)づけする」— 本プロジェクトの独自機構(ConTree operation UUID/image IDへの錨付け)を名指す。npm・GitHubとも空き確認済み(2026-09-29実測)
- ディレクトリ `_incubator/runanchor/`・本ファイル名も追従済み

### 先行技術スイープの追記(receipt系クラスタ・レビュー実調査)

§USPの先行技術列挙(Pipelock/OpenHands/SWE-agent/GitHub reviews)に加え、同名・同領域のクラスタを実名列挙する:

| 先行 | 内容 | 残る差分 |
|---|---|---|
| `RLASAF12/agent-receipt`(npm) | MCPミドルウェアで全tool callに暗号receipt・ghost action検出 | プロバイダアンカー無し・自己計測止まり |
| `ametel01/agentreceipt` 他同名3件 | coding sessionの証拠sidecar+`verify diff` | 同上 |
| `mohamedzhioua/agent-done-or-not` | 「"it works"が信頼の主張でなくreceiptになる」・CI assertモード+SHA256 receipt | 同上 |
| `shaheershoaib/receipts` | 「Agents need receipts: re-prove an AI fix before you trust it」 | 同上 |
| Sembl / verik / truth / prove-it / toolproof | 完了申告の検証系(verikは23決定論的チェック+CI統合) | 同上 |
| depot.dev「CI for agentic engineering」/ Pondero「CI for agents」 | 「CI for agents」句・概念は構築中・占有済み | run単位の台帳・関所品質の計量は無し |

**残る真の差分(占有なし・v1.1 §USPと不変)**: ①プロバイダ発行アンカー(ConTree UUID/image ID+image fork再実行 — 全先行は自己計測またはローカルhash止まり)②run単位台帳(却下済み含む)③関所品質の計量(撒き種コーパスへの感度/特異度)

### 課題の言い方(3層構造・確定)

- **層1(冒頭1行)**: 「CIは成果物を疑う。**エージェントの『報告』を疑うものはない**」/「CIは最終diffを見る。runは見ない」
  - ※「エージェント版CIが無い」は**使わない** — エージェント製PRは既に通常CIを通るため反論で崩れるし、「CI for agents」句自体が占有済み。存在主張ではなく差分主張に転換
- **層2(課題節本文)**: ボトルネック移転の構造論。修飾「タダ」は削り出典つきに — 「生成の単価が人間の執筆時間を大きく割り込んだ一方、確認コストは人間の時間のまま」
  - 出典候補(レビュー調査済み): Sonar State of Code 2026(コミット済みコードの42%がAI製・96%が完全に信用せず・38%が「AIコードのレビューは人間のより工数がかかる」)/ Cognition公式「code review—not code generation—is now the bottleneck」/ AWS CTO Vogels「verification debt」/ arXiv 2609.17598(37,623件のagent PR・Devin PR revert率14.5%)
- **層3(デモクライマックス)**: 「怖いのは失敗ではなく『成功と言われた失敗』— そしてreceiptがある世界では、その嘘はプロバイダの記録と突き合わせて再実行すれば物理的に成立しない」
  - 「嘘を暴く」のビート自体はカテゴリ定型句(verik等も使用)。オチは固有機構(プロバイダ照合+再実行)に着地させる

### 問題の質(6属性・新設)

| 属性 | 証拠 | 状態 |
|---|---|---|
| よくある | Sonar調査: コミット済みコードの42%がAI製(2027年65%予測) | 証拠あり(出典要固定) |
| 増えている | 同上+エージェント導入の普及トレンド | 証拠あり(出典要固定) |
| 急ぐ | arXiv 2609.17598: Devin PRのrevert率14.5% = 未検証のまま入った変更の実害が実測されている | 証拠あり |
| 高くつく | Sonar: 38%が「AIコードのレビューは人間のより工数がかかる」・59%が検証工数を中〜大と回答 | 証拠あり |
| やらざるを得ない | 規制・義務なし。正直な書き方:「required reviewsがあるrepoでは人承認自体が既に必須。receiptはその必須行為を根拠付きでできるようにする」 | 証拠一部(型を変えて記載) |
| 頻繁 | エージェントの実行ごと(ヘビーユーザーなら1日数十回)。実測値は自運用(AGENT_LEDGER)のrun頻度で裏付け可能 | 証拠あり |

証拠あり5/6+一部1 = Gate 0基準(「証拠なし」3つ以上で差戻し)をクリア。

### 審査員視点での残留意点(レビューより)

- Impact: 層2+出典で強化 / Design: デモ構成に寄与 / **Idea: 層1が差分主張に修正されれば「また検証ツールか」減点を回避** / Technological Implementation: フレーミングは無効 — 自律1ループ+verify実装が引き続き本体
- CI比喩はフックとしてのみ使い、血統主張にはしない(正確な祖先はrequired reviews+SLSA/in-toto provenance)
- verify実装はConTreeでのimage fork+再実行=重い外部依存。「軽いCIプラグイン」を期待させない

### 宿題の状態変化

- リスク#4(命名衝突)は**改名により解消**。新リスク: runanchor名の定着は今後の提出物で統一して使うこと
- Gate 0宿題(人間作業)は不変: Token Factoryクレジットのみサインアップ→`contree run`実測が技術検証第1号

---

## 追補3(2026-09-29夜・クレジット適用とConTree機構のコードレベル確認)

### クレジット・認証の実測状況(リスク#2の更新)

- **プロモコード $25 適用完了**(Devpost経由・Nebius公式メールで発行。コード値は公開repo化を見据えて本書には記録しない)
- **追加$25の道あり**: Nebius Builders Program(dev.nebius.com/builders)参加でToken Factory追加クレジット+Tavily/Academy特典(Devpost案内メール記載・未申請)
- **カード入力の扱いが確定**: Nebius公式メールが「billing address または credit card を求める場合がある。bot対策の$0認証課金のみ・他の課金はなし」と回答。ドキュメント矛盾は「カード登録はあり得るが課金は発生しない」で解消(CEO制約「課金なし」は維持)
- **予算の硬化(2026-09-29・CEO裁定)**: **提供クレジット残高を上限として死守・追加課金は一切しない**。計量(コーパスn数)・verify・エージェント自律ループなど全外部実行の回数は残クレジットから逆算して設計する。初回実行時に1実行あたりの消費を実測し、以降の実行計画はその単価で見積もってから承認を取る

### メンテナンスによる検証の一時ブロック

- Token Factoryが 2026-09-29 09:00–17:00 UTC(= JST 18:00–9/30 02:00)の計画メンテナンス。**APIキー管理・endpoint変更が不可**(既存endpointのトラフィックは正常)
- `contree auth`用のAPIキー発行はメンテ明け待ち → **技術検証第1号は9/30以降に延期**(ブロッカーは外部・期限への影響は軽微)

### ConTree機構のコードレベル確認(USP-1外部アンカーの裏付け)

- `contree-cli 0.9.4` / `contree-client 0.4.0` をローカル導入済み(`uv tool install`)
- `models.py`実物で `OperationResponse` を確認: `uuid`・`image_uuid`(実行元)・`result_image_uuid`(生成物)・`status`・`duration`・`consumed_cpu`/`consumed_memory`/`image_size`(**コスト実測の根拠**)・`metadata.command`・`result`(exit code)
- `contree op events UUID` でstdin/stdout/stderr/exitのrawイベント列を取得可能 → 「テストログの実在」証拠の取得経路が確定
- **verify物理手順の確認**: `contree -S <key> use <image_uuid>` で記録imageへのforkがCLI機能として実在 → 「image fork→コマンド列再実行→結果比較」は実装可能。詳細は `research/contree-notes_runanchor_20260929.md`
- 注意: 以上はコード・docsの確認であって**実行検証ではない**。`contree run`実測(APIキー発行後)まで「動くはず」と断定しない(未確認リストは同researchファイル §4)
