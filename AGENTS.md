# runanchor — プロジェクト作業指示

Nebius × NVIDIA Global AI Hackathon(締切 2026-10-30 10:00 PDT・約10/31 02:00 JST)への提出用repo。Coding & Agentic Engineering トラック。Studio憲法(`~/Developer/AGENTS.md`)に従う。

## 何を外に出すか

コーディングエージェントの各実行(run)を、プロバイダ発行の実行記録(ConTree operation UUID/image ID)に錨づけた検証可能なreceiptにし、人(または計量モードの機械レビュアー)が承認して初めて採用になる関所ツール。

- 製品仕様の正本は `submit/description.md` / `README.md`。bd/配下は設計経緯の記録
- 旧名 `agent-receipt`(npm/GitHubで4重占有のため改名・bd/追補2参照)

## 言語規約(このプロジェクト固有)

- **提出物は英語**: README・submit/・コード・コメント・動画テロップ
- **内部文書は日本語**: bd/の事業設計・DEC・作業記録
- 英語成果物を出す前に、Ownerへ日本語ダイジェストを添えて検収する

## repo境界

- **このディレクトリは独立したgit repo**。他プロジェクト(`../sagi-shield/`等)への参照・依存は禁止。必要ならコピーして内包する(出典をコメントに残す)
- 本repo内の全成果物はファイル名にslug `runanchor` を冠する(bd/のIDEA-*・DEC-*等)

## 禁止事項

- **提供クレジット残高を上限として死守・追加課金は一切しない**(2026-09-29・Owner裁定)。外部実行(サンドボックス・推論・verify)は残クレジットから逆算した回数のみ、実行前に単価実測→見積→承認の順で行う
- Token Factory/Nebiusの実操作・課金・外部公開(GitHub公開化・YouTube投稿・フォーム送信)はOwnerの人間承認なしに実行しない
- 秘密情報・APIキーのコミット禁止
- Gate未通過での実装着手禁止(bd/の事業設計ワークフローが先行)

## 検証

実装検証: `./scripts/verify`(pytest全量・オフライン)。コーパス検証: `python3 scripts/validate_corpus.py`(oracleがseed状態で罠を検出するか)。packaging: `python3 scripts/check_packaging.py`。提出前ゲート: `python3 scripts/ready.py`。コミット前は `_ops/hooks/check_doc_claims_gate.py` がVERIFYマーカーを機械検査する(親repo側フック)。

## 関連

- 事業設計スキル: `~/.agents/skills/business-design/`(成果物は `bd/` に置く)
- 提出物規約の正本: `~/Developer/_ops/docs/SUBMISSION_WORK_CHECKLIST_20260926.md`
- 勝者の作法: `~/Developer/_ops/docs/REF-hackathon-winners-playbook_20260927.md`
