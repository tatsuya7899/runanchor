# runanchor — 設計

**前提**: SPEC-runanchor_requirements.md(レビュー済・[要確認]残り0件)
**日付**: 2026-09-29

## 方式(何をどう作るか)

Python製CLI `runanchor`。エージェント本体=Nemotron(Token Factory推論API・OpenAI互換想定)が計画したコマンドを、**ホスト側のドライバが `contree` CLI経由でConTreeサンドボックスに投入**する。各 `contree run` はプロバイダ側のoperationを生成するため、**ドライバはoperationレコード(uuid・image_uuid・result_image_uuid・コマンド・exit code・ストリーム指紋・consumed_*)を回収して検収書JSONとして台帳(jsonl)に追記**する。関所=台帳のpending行を人(CLI)/機械(計量モードのNemotronレビュアー)が採否する状態機械。verify=`contree use <image_uuid>` で記録開始imageへfork→記録コマンド列を-D(使い捨て)で再実行→終了コード+ストリーム指紋+result_image有無を比較。**デモモードはドライバの差し替え**(実contree呼出しをfixture再生に替える注入点)で実現し、ドメイン層(receipt/台帳/関所/計量)はAPI非依存で全単体テスト可能にする。

## 触るファイル(名指し)

| ファイル | 変更内容 | 新規/既存 |
|---|---|---|
| `app/runanchor/cli.py` | エントリ: `run` / `list` / `show` / `approve` / `reject` / `verify` / `bench` / `--demo` | 新規 |
| `app/runanchor/agent_loop.py` | Nemotron駆動ループ(書く→走る→赤→直す→緑)。コマンド列を生成しドライバへ渡す。**停止条件**: テスト緑到達 or 最大反復数(設定値)到達。give-upで終わった系列も最終receiptに`unresolved`印を付けて台帳化 | 新規 |
| `app/runanchor/contree_driver.py` | `contree` CLI薄ラッパー(subprocess・`-o json`・-Sセッション)。**注入点**: `DemoDriver`が同一IFでfixture再生 | 新規 |
| `app/runanchor/receipt.py` | 検収書スキーマ・発行(operation→receipt写像・ストリームSHA256・diff指紋) | 新規 |
| `app/runanchor/ledger.py` | jsonl追記台帳+状態機械(pending→adopted/rejected/mismatch)。削除機能を持たない | 新規 |
| `app/runanchor/gate.py` | pending一覧・approve/reject(理由必須)・判定主体の委譲IF | 新規 |
| `app/runanchor/judge.py` | 計量モード用Nemotronレビュアー(検収書の証拠のみ入力・採否+理由を構造化出力) | 新規 |
| `app/runanchor/verifier.py` | 再実行比較。**検証単位=個別receipt**(そのreceiptの`image_uuid`へfork→そのreceiptの`command`を-D再実行)。比較対象=終了コード・stdout/stderr指紋・result_image有無 | 新規 |
| `app/runanchor/bench.py` | 撒き種コーパスランナー+混同行列+感度/特異度レポート | 新規 |
| `app/runanchor/demo.py` | fixture読込・デモ採点の固定経路 | 新規 |
| `app/fixtures/` | デモ用: 記録済みoperation応答・receipt列・撒き種repoスナップショット | 新規 |
| `app/corpus/` | 撒き種タスク定義(task・seededバグ・正解ラベル・既存テスト緑) | 新規 |
| `app/tests/` | pytest群(下記テスト方針) | 新規 |
| `scripts/verify` | 単体+E2E(オフライン)一括。ライブ系は別フラグ | 新規 |
| `README.md`(英語化) / `LICENSE` / `submit/` | 提出物整備 | 既存更新 |
| `bd/SPEC-runanchor_tasks.md` | 段3タスク表 | 新規 |

## 既存アーキテクチャとの整合

- repo境界: 他プロジェクトへの参照・依存なし。sagi-shieldで確立した構成(flat `app/` + `scripts/verify` + fixtures + 台帳jsonl +「DEMO」区別表示)を**パターンとして踏襲**するが、コードのコピーは行わず本repoで新規実装(AGENTS.mdのrepo境界に適合)
- 認証: `contree auth` はユーザー管理・`~/.config/contree/auth.ini`にCLI自身が保管。runanchorは認証情報を読まず、`contree`バイナリを子プロセスとして呼ぶだけ(公式「Agents must never run `contree auth`」に整合)
- SSOT: 検収書は`ledger`のjsonlのみが正本。派生表示(show/list/レポート)は全て台帳から再生(複製データを持たない)

## データモデル・インターフェース

### 検収書(receipt)JSON — 台帳1行=1検収書

```json
{
  "receipt_id": "uuid", "task": "slug", "run_seq": 3,
  "operation_uuid": "contree-op-uuid",
  "image_uuid": "start-image-uuid", "result_image_uuid": "end-image-uuid",
  "command": "pytest -q", "cwd": "/work", "shell_mode": false,
  "status": "SUCCESS", "exit_code": 0,
  "stdout_sha256": "...", "stderr_sha256": "...", "stdout_tail": "末尾N行",
  "diff_sha256": "...（算出方法=作業dirのexport tarハッシュまたは内部manifestのsha256・決定論的に記録）",
  "duration_s": 12.3,
  "consumed_cpu_s": 8.1, "consumed_memory": 262144, "consumed_memory_unit": "実測で確定(getrusage由来・bytesとは限らない)",
  "model": "nemotron-...", "seed": 42, "seed_note": "推論APIがseedを受け付けるか未確認・不可ならnull", "issued_at": "iso8601",
  "state": "pending|adopted|rejected|mismatch",
  "decision": {"by": "human|judge:<model-id>", "reason": "...", "at": "..."},
  "demo": false
}
```

- `demo:true` + fixtureアンカーの検収書は「DEMO」区別表示(FR-6・誠実性)
- 台帳: `state/receipts.jsonl` + タスク単位の系列は `task` + `run_seq` で再構成
- ドライバIF(注入点): `run(cmd, files, disposable) -> OperationRecord` / `use(image) -> None` / `events(op_uuid) -> EventLog`。`ContreeDriver`(実CLI)と`DemoDriver`(fixture)が同一IFを実装

### 判定主体

- 人間モード: `gate.pending()` → `approve(id)` / `reject(id, reason)`
- 計量モード: `judge.review(receipt_evidence) -> {adopt|reject, reason}` — 入力は検収書の証拠部のみ(task文・diff・テストログ末尾・exit code)。正解ラベル・operation原データは渡さない(非循環)

## 撒き種コーパス設計(計量の正解データ)

- 型(「テスト赤」型は最小化・主軸は潜る系): ①既存テスト緑だが仕様外の簡略化(閾値ずらし・条件抜け) ②ログ偽装(「PASSED」を吐くが実行していない) ③対象外ファイルへの余計な変更 ④報告とdiffの不一致(「直した」と言いつつ未変更)
- 各タスク: `task.md`(指示)・`seed/`(種込みrepo状態・初回runで `--file` マウント経由でサンドボックスへ注入)・`label.json`(seeded/clean・bug_type)・`oracle`(正解の性質)
- 初回規模: seeded≈24・clean≈11(要件の成功基準どおり)。生成は既存小規模repoへバグ注入する生成器 + 手作り精選の混合

## 非機能(性能・権限・セキュリティ・ログ)

- 権限: サンドボックス実実行・推論課金は実行前に残クレジット照合+承認確認(AGENTS.md禁止事項第1条)。`--demo`経路は一切の外部呼出しを持たない
- 秘匿: CONTREE_TOKEN等は読まない・レシートに環境変数を焼かない。judge/benchへ渡す証拠から秘密候補(トークン形式文字列)を落とすサニタイズを実装
- 失敗時: contree呼出し失敗/タイムアウトは検収書を「発行不能」ではなく `status` 記録つきで発行(失敗の試行も台帳の対象・FR-1)。verifyで`use`不能(image欠落)は「検証不能」として不一致とは区別して返す
- ログ: ストリームは指紋+末尾N行のみ台帳へ(全文は別ファイル参照・台帳肥大と秘匿を防ぐ)

## 検討した代替案と却下理由

| 案 | 却下理由 |
|---|---|
| もっと単純な案: agentの報告をただ記録するログツール(再実行・外部アンカーなし) | 核心差分(プロバイダ照合+run単位台帳+計量)が消え先行receipt系と同値になる。USPが崩壊 |
| contree_client(Python SDK)直利用 | セッション/履歴管理を自前実装し直すことになる。公式CLIはagentプロトコル整備済み(`contree agent`)。verifyでSDK併用はあり得るがMVPはCLI統一 |
| エージェントをサンドボックス内で動かす | 自身のoperationを観測できない(内側から外側の記録は取れない)。ホスト駆動一択 |
| 関所判定を決定論ルールのみ | 「既存テスト緑だが潜る」系は意味判定が要りルールでは捉えられない。計量モードはLLM判定主体が要件(FR-7) |
| 台帳をSQLite | jsonlで十分な規模・git差分可読・追記のみで監査向き。複雑な検索要件はMVPに無い |
| 薄いWeb UI | 人間裁定でMVP外確定(デモ要件はtest buildで充足) |

## テスト方針(受入シナリオ→テストの対応)

| 受入シナリオ# | テスト種別 | 機械判定できるか |
|---|---|---|
| 1(検収書発行+外部参照) | 単体(DemoDriver+operation fixture) | 可: receipt生成・UUID項目・demo印 |
| 2(詳細表示の5項目) | 単体 | 可: 表示フィールド存在・非空 |
| 3(採用→台帳記録) | 単体 | 可: 状態遷移+台帳行 |
| 4(却下→理由必須・残存) | 単体 | 可: 理由空で拒否・行残存 |
| 5(再検証の復元→再実行→比較) | 単体(フェイクdriver)+ライブE2E(承認制) | 可(フェイクで一致/不一致両経路) |
| 6(不一致検出→マーク) | 単体(改竄fixture) | 可 |
| 7(デモモード・外部接続なし) | E2E(ネットワーク遮断環境変数で誤呼出し検知) | 可 |
| 8(計量モード・感度/特異度出力) | 単体(ミニコーパス n=4+2・judgeフェイク)+ライブ計量(承認制) | 可(出力形式・行列計算) |
| 9(自律1ループ→系列表示) | E2E(fixture再生ループ)+ライブ(承認制) | 可(系列のreceipt数・順序) |

## 未確認の設計前提(技術検証第1号で潰す・設計変更は起きない前提の粒度)

- サンドボックス実行の課金単位・`use <image_uuid>`のfork可否・Nemotron推論エンドポイント形式 — いずれも「実行計画・コスト見積・judgeモデル選定」に効くが、アーキテクチャ(注入点・台帳・関所)を変えない。実測後にresearchノート §4 へ追補し、判明した制約は本書へ追補する
- 残クレジット照合の方法(コンソール確認/API問い合わせ/実行前の手入力宣言)・`consumed_memory`の単位・推論APIのseed対応 — 同上・実測で確定
