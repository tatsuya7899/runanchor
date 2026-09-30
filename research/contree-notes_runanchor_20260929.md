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
- [ ] サンドボックス実行の課金単位(consumed_cpu/秒課金か・$25で何runできるか) → **ベータ中は無料**(下記追補)
- [ ] Nemotron(Token Factory推論API)のエンドポイント形式(OpenAI互換か)と料金 → **下記追補で確認済み**
- [ ] `contree run` のネットワーク遮断可否(検証の再現性に影響)
- [ ] **[レビューP0-1・最重要]** `-D`(disposable)再実行の `op show` が `result_image_uuid` を返すか。返らない場合、verifyの「終了image有無」比較軸が構造的に偽不一致を量産 → 比較軸を落とすか再実行を非disposableにする設計変更が必要(FR-5の内部緊張)
- [ ] **[レビューP1-3]** `contree -o json run` の実出力がspawn時に `uuid` を含むか(含めば正しいアンカー。含まなければ `op show HEAD` フォールバック=誤帰属リスクあり・receipt.anchor_source="head"で区別表示)
- [ ] **[レビューP1-2]** `op show` JSONの実フィールド名(実装はmodels.py準拠: `result.exit_code`・`duration`・`consumed_cpu`/`consumed_memory`フラット・`metadata.command`)。失敗runの `contree run` rcがコマンドexit codeを反映するか(反映するならdriverの縮退経路が本線になる)

## 5. 追補(2026-09-29夜): 推論API調査 + Sandboxesベータ申請状況

### Sandboxesベータ

- **クローズドベータ**: コンソールのSandboxes画面から「Request beta access」フォーム送信(project ID+email+use case)。承認待ち。トークン自体は有効(auth済み)で、権限付与でそのまま使える
- **ベータ期間中はサンドボックス実行が無料**(コンソール表記 "Free while in beta — runs don't consume your credits")→ 予算モデルが変わる: $25はほぼ推論のみに使える
- 注意: beta中は個人情報・機密データをサンドボックスに入れない(公式注意書き)

### 推論API(Nemotron)— 確定情報

- **OpenAI互換**: `https://api.tokenfactory.nebius.com/v1/chat/completions` + `Authorization: Bearer $NEBIUS_API_KEY`(contreeと同じAPIキー。リージョン別ホストあり: `api.tokenfactory.us-central1.nebius.com` 等)
- **モデルカタログ**: https://tokenfactory.nebius.com/model-catalog.md (JSON正本: /api/public/models_info)
- **NVIDIA OSSモデル(ハッカソン要件充足候補)**:

  | モデル | 料金(入力/出力・$ per 1M) | ctx | region |
  |---|---|---|---|
  | `nvidia/Nemotron-3_5-Lightning` | **0.06 / 0.24** | 1024K | eu-north1 |
  | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | 0.06 / 0.24 | 262K | eu-north1 |
  | `nvidia/nemotron-3-super-120b-a12b` | 0.30 / 0.90 | 256K | us-central1 |
  | `nvidia/Nemotron-3-Ultra-550b-a55b` | 1.00 / 3.00 | 1024K | us-central1 |

- **コスト感**: Lightning/Nanoで1run系列≈100K in/20K outとして約$0.011 — コーパス35件でも$1未満。**サンドボックス無料と合わせ、クレジット制約は実質緩和**(judgeをSuper等に上げても数$規模)
- **SWE-bench環境がプリロード**: SWE-bench Verified / SWE-rebench / V2 — 撒き種コーパスを自前だけでなく既知バグの標準ベンチから取れる可能性(第三者再現可能性にも強い)
- Mini-SWE-Agent連携あり(`mini-swe-agent[contree]`)— ただし公式docs自身がContreeEnvironmentのSDK互換バグを報告(2026-09時点)。自前ループが無難だが参照実装として価値あり

### 未確認(ライブ推論テストで潰す)

- [x] seedパラメータを受け付けるか・効くか → **受理されるが決定性なし**(実測: seed=42・temperature=0.7・同一プロンプト2回で応答が非一致。receiptのseed項目はnullable/参考値として扱う・再現の根拠にはしない)
- [x] 同じAPIキーで推論APIが即使えるか → **可**(contreeと同じトークンでchat completions成功)
- [ ] 構造化出力/JSON mode対応(judgeの判定を厳格化するなら) — docsに「Structured output & JSON」ページあり・未実測
- [ ] SWE環境の具体的な起動方法(images一覧で見える命名規則)

### 実測メモ(2026-09-29)

- `nvidia/Nemotron-3_5-Lightning` は**reasoning系モデル**: 出力が思考過程で始まり、`max_tokens`はreasoning tokensも消費する(200で思考途中切断)。judge/agentのプロンプト設計は最終回答の抽出を前提にする・max_tokensに余裕を持つ
- 最小呼び出しの実コスト: 31 tokens(21 in/10 out)≒$0.000004 — 実測でも無視できる単価

## 6. 追補2(2026-09-30): Sandboxesベータ承認・ライブ#0検証の実測結果

**承認**: 件名「Welcome to Nebius Token Factory Sandboxes Beta」(contree@nebius.com・2026-09-30 07:33 UTC)。`contree images`で3,000+イメージ取得成功(権限付与を実機確認)。ベータ中の同時実行上限=50ops。

### 実runのJSONスキーマ(foreground・`-o json`・実測値)

非使い捨てrun(`contree -S ra_probe -o json run -- echo hello-runanchor`):

```json
{"uuid": "01a0f146-...", "kind": "instance", "status": "SUCCESS",
 "duration": 1.298, "image_size": 926,
 "result_image_uuid": "b2516231-0903-440d-920f-9f638c2f9b81",
 "metadata": {"result": {"stdout": {"value": "hello-runanchor\n", "encoding": "ascii", "truncated": false},
   "stderr": {"value": "", "encoding": "ascii", "truncated": false},
   "state": {"exit_code": 0, "timed_out": false}}},
 "result": {"image": "b2516231-...", "tag": null},
 "exit_code": 0, "image": "b2516231-...", "tag": "",
 "stdout": "hello-runanchor\n", "stderr": "", "error": ""}
```

`op show`(UUID・HEAD参照とも可)は同系統のフラット形:

```json
{"uuid": "...", "status": "SUCCESS", "exit_code": 0, "duration": 0.438,
 "result_image_uuid": "b2516231-...", "kind": "instance", "image_size": 0,
 "image": "b2516231-...", "tag": "", "error": "",
 "result": {"stdout": "hello-runanchor\n", "stderr": "",
   "state": {"exit_code": 0, "timed_out": false}}}
```

### #0検証の結論(§4未確認リストの全解決)

- [x] `contree run`は実際に動く → **動作確認済み**(ベータ中無料)
- [x] operation UUID/`op show`実レスポンス → **上記スキーマで確定**
- [x] `use <image_uuid>`で過去imageへforkできるか → **可**(b2516231…から`use`→run→同image UUIDが再出現)
- [x] **[P0-1] `-D`が`result_image_uuid`を返すか → 返らない(`null`)**。disposable=checkpoint不生成が仕様。**設計変更確定: verifyの再実行は`-D`ではなく、verify専用セッション(`ra_verify_<receipt_id>`)での非使い捨てrunとし、生成checkpointの`result_image_uuid`を比較に使う**(セッションはverify完了後に`session delete`で掃除)
- [x] **[P1-3] `run -o json`がspawn時に`uuid`を含むか → 含む**(foregroundでも全フィールドが1オブジェクトで返る → anchor_source="run-json"が本線で安定)
- [x] **[P1-2] `op show`の実フィールド名 → 実測確定**: フラットに`uuid`/`status`/`exit_code`/`duration`/`result_image_uuid`/`image`/`kind`/`image_size`/`tag`/`error`+`result.{stdout,stderr,state.{exit_code,timed_out}}`(run出力とは階層が一部異なる → パーサは両形を許容する必要あり)
- [x] 失敗runの形: `run -- false` → **`status:"SUCCESS"`・`exit_code:1`**(status=オーケストレーション成否・exit_code=プロセス終了コード・分離)。CLIのrcはパイプ処理の関係で未確定だが、JSONのexit_codeが正本
- [x] `--file host:inst`マウント → **動作確認済み**(/tmp/ra_mount_test.txt→/work/mounted.txtの内容がcatで一致)
- [x] **同一コマンド再実行で同一`result_image_uuid`** → 確認(echo同一文でb2516231…が2回出現・imageは内容アドレス化/重複排除されている → 「終了状態一致」の比較軸として生きる)
- [ ] `consumed_cpu`/`consumed_memory`/`created_at`の実フィールド(今回の最小runでは非露出・コスト実測時に確認)
- [ ] ネットワーク遮断可否(未確認)
- [ ] SWE環境の命名規則(未確認・`images --prefix=`で探す)

### 設計への影響(実装修正タスク)

1. `run`のJSONパーサを実スキーマに合わせる(フラットフィールド+`metadata.result.{stdout,stderr,state}`+`result.{stdout,stderr,state}`の2形態)
2. **cwdは`-C`フラグへ変更**(現行の`sh -c`での`cd`ラップは廃止 — `-s`内のcdは公式非推奨)
3. **verifyは-Dを廃止しverify専用セッション+非使い捨てrunへ**(result_image_uuid比較軸を維持。セッションは`session delete <key> -y`で掃除)
4. `status`の実語彙は`SUCCESS`/`FAILED`等(models.py準拠だが値域確認済み)
5. セッションキー規約: `runanchor_<ledger>-<seq>`・verifyは`ra_verify_<receipt_id>`(-Sフラグ運用・env依存禁止は既設計どおり)

## §7 追補(2026-09-30・同日) — e2e実施後の設計再修正: image一致軸は却下

§4の判定を実装後のライブe2e(`scripts/e2e_live_runanchor.py`)が**覆した**。最終設計は再修正済み。

### 追実測の結果

| 実験 | 結果 |
|---|---|
| 同一セッション内・同一コマンド再実行 | 同一`result_image_uuid`(b2516231…/09a76e8d…) — 同一セッション内では再現する |
| 別セッションへ`use <image_uuid>`でfork→run(fs非変化コマンド) | 同一image UUID(09a76e8dがそのまま = checkpointが親imageと同一) |
| **別セッションで`use <同一base>`→`-C /work`の同一コマンド** | **image UUIDが毎回異なる**(work run=b27ae490…、verify run=04b80e1f…、probe6=9d2dfa13…、probe7=e82f0702…) |
| e2e(`echo runanchor-e2e`@-C /work →receipt→verify) | exit_code/stdoutは一致・**result_image_uuidのみ不一致でmismatch判定** |

### 解釈と確定設計

- セッション内再現は**セッションキャッシュ**(同一session+parent+commandでのcheckpoint再利用)と推定。クロスセッションではcheckpointは非再現(workdir初期化等に実行ごとの識別子/時刻が混入する形)
- **確定: `result_image_uuid`は比較軸から除外**。比較すると正直なrunまで全件mismatchになる構造的欠陥
- verifyは**`-D`に復帰**(image比較を捨てたのでcheckpoint生成不要・副作用ゼロ・最安) + verify専用セッション + `close()`(=`session delete`)で掃除
- 比較軸の最終形: `exit_code` + 正規化stdout指紋 + 正規化stderr指紋 の3軸。終了状態の等価性は測れないものとして正直に非対象とする
- e2e実績: work op `01a0f15b-3f4b-7727-85d3-7c7df7113f47` → receipt `26c2bd0c` → replay op `01a0f15b-4911-76f7-b8b5-60e659c816eb` → **verdict `match`**

### §4チェックリストの訂正

§4の「同一コマンド再実行で同一result_image_uuid → 比較軸として生きる」は**同一セッション内に限る**と訂正。§4のverify専用セッション非disposable案はe2eで却下、`-D`復帰が確定。実装は`verifier.py`・`contree_driver.py`のdocstringに反映済み。
