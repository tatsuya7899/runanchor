# ConTree API 実測調査 — runanchor 設計用メモ
Created: 2026-09-29 / 出所: contree-cli 0.9.4(`contree agent`全量)+contree-client 0.4.0 `models.py`+公式docs(tokenfactory.nebius.com/sandboxes)。**実アカウント実行は未検証**(メンテ中・APIキー未発行のため)。実行確認が取れたら本ファイルに追補する。

## 1. 検収書に刻めるもの(OperationResponse・models.py実物)

| フィールド | 意味 | receiptでの役割 |
|---|---|---|
| `uuid` | operation UUID | **外部アンカー本体** |
| `image_uuid` | 実行元imageのUUID | 開始状態の指紋 |
| `result_image_uuid` | 生成imageのUUID(SUCCESSのみ) | 終了状態の指紋 |
| `status` | PENDING/ASSIGNED/EXECUTING/SUCCESS/FAILED/CANCELLED | オーケストレーション結果(プロセスexitと別) |
| `duration` / `consumed_cpu` / `consumed_memory` / `image_size` | 壁時計・CPU秒・peak RSS・書込みバイト | **コスト実測**($換算は別途) |
| `created_at` | ISO8601 | タイムスタンプ |
| `metadata` | OperationInstanceMetadata(command等) | 実行コマンド列 |
| `result` | OperationResult(exit code等) | 成否 |

- `Image.operation_uuid` で逆引きも可能(image→作成operation)
- イベントストリーム: `contree op events UUID` でstdin/stdout/stderr/exitのrawイベント列を取得 → **「テストログの実在」はここから証拠化できる**
- `contree -o json run -d -- cmd | jq -r .uuid` でspawn時にUUID確保(detached)。foregroundでも `-o json` でoperation metadataが取れる

## 2. verify(再実行)の物理手順 — 設計の中核

```
contree -S verify_<receipt_id> use <image_uuid>     # 記録された開始imageへfork
contree -S verify_<receipt_id> run -D -- <記録コマンド>   # 再実行(-D=image汚染しない)
contree -S verify_<receipt_id> op show HEAD         # exit_code/stdoutを比較
```

- `use <UUID>` は任意imageへのbind=**image forkがCLI機能として実在**。session branch `--from` でも可
- セッション履歴はDAG(use/runノード+parent辺)。`session show`で全履歴、`session rollback`で遡れる → receiptの「run単位台帳」はConTree履歴と1:1対応できる
- `--disposable`(-D)実行はcheckpointを残さない = 再現検証側は常に-Dでよい。計量側(成果物を残す)はnon-disposable

## 3. エージェント運用規約(公式・contree agentより)

- `-S <key>` を全コマンドに付ける(env依存禁止)。session=agent memoryとして再利用
- **1 run=1 mutating step**(チェインするとcheckpointが潰れる)
- global flags(-S/-o/-p)はサブコマンドの前
- `contree auth`はエージェントが実行してはいけない(ユーザー管理) ← runanchorの関所設計と相性が良い
- 実行形態: direct(デフォルト)/`-s` shell/`-I` interpreter/piped stdin/`-d` detached
- `--file host:inst` でローカルファイルをマウント(SHA256 dedup・デフォルト除外 .git/__pycache__/node_modules等)
- `contree env KEY=VAL` セッション環境変数、`--preserve-env` でimageへ焼き付け
- `contree build` = Dockerfile実行(FROM/RUN/COPY/WORKDIR/ENV/ARG/USER・multi-stage未対応)
- `contree tag` でimageに名前。プロジェクトscope(別プロジェクトは別scope)

## 4. 未確認リスト(contree run実測時に潰す)

- [ ] `contree run` が実際に動くか(クレジットのみの環境で)
- [ ] operation UUID/`op events`の実レスポンス(項目名・ログの完全性)
- [ ] `use <image_uuid>` で過去imageへ本当にforkできるか(他人でなく自分のimageでも)
- [ ] 7,000+プリロードSWE環境の一覧・選び方(`contree images --prefix=`で見える範囲)
- [ ] サンドボックス実行の課金単位(consumed_cpu/秒課金か・$25で何runできるか)
- [ ] Nemotron(Token Factory推論API)のエンドポイント形式(OpenAI互換か)と料金
- [ ] `contree run` のネットワーク遮断可否(検証の再現性に影響)
