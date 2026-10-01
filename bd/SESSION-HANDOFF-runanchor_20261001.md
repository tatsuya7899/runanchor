# SESSION-HANDOFF — runanchor 提出完了・Zenn記事化まで (2026-10-01)

**English summary** — Final session record. runanchor was fully shipped: public GitHub repo, YouTube demo (2:04), Devpost submission verified live, `ready.py` 23/23. Follow-on work: a Japanese Zenn article was drafted, adversarially reviewed, linted (natural-japanese, 0 findings), and published by the owner (Tech category). All claims were re-verified against `eval/bench-20261001-v4.*` row-level data before writing. Known carry-over: 4 local commits in `zenn-articles` remain unpushed (push is human-only there); 1 local commit in this repo (this file) is unpushed. Hackathon results expected ~Jan 2027. Total inference spend stayed within credits (console $0.30 through 10/01 + v4 est. ~$0.4 unposted).

## セッション範囲

v4ベンチ反映直後〜Devpost提出完了〜Zenn記事公開まで。runanchorプロジェクトのShip完了セッション。

## 完了したこと(証拠つき)

### 提出物の確定

| 成果物 | 状態 | 根拠 |
|---|---|---|
| 動画 v4版 | `submit/runanchor-demo.mp4`・123.9s・3.4MB・h264/AAC | Scene5音声をOwner再録音版へ差し替え(`e90a166`)。新値64%/7/11→100%/11/11・42/43と音声一致 |
| GitHub公開 | `tatsuya7899/runanchor` → PUBLIC | `gh repo view`で確認。push済み(公開前スキャン: 秘密情報・個人情報ヒットなし) |
| YouTube | https://youtu.be/Z-NM0GLORFA | タイトル+説明文をclaims表のverified範囲で作成・Owner投稿 |
| Devpost | https://devpost.com/software/runanchor-receipts-your-coding-agent-can-t-fake | 提出完了・公開ページを実機fetchで2回確認 |
| ready.py | **23/23** | URL転記後(`1e4e1ae`) |

### 言語監査(提出物は英語規約)

- `submit/`内の日本語3ファイル(form-answers・narration-claims・narration-text)を全英語化
- 内部文書(`bd/`・`AGENTS.md`・`eval/BASELINE.md`・`research/`)はOwner裁定で**日英併記**に(15ファイル冒頭へEnglish summary挿入・`bd/README.md`を案内として新設)。「過程も作品に」の方針
- コミット: `5782fb0`・`78aa4dd`

### Devpost全欄の対応

- Elevator pitch: 169字版(`Agents say "tests pass." Who checks?…`)
- Project Story: `submit/project-story.md`新規作成(Inspiration/Challenges/学び構成)
- ギャラリー: `runanchor-thumbnail.png`(3:2・0.05MB・動画と同一デザイン言語のレンダラ`render_thumbnail_runanchor.py`)+動画フレーム3点
- Additional info: 全13欄の下書きを`form-answers.md`へ(Nemotron評価8/8/8・Tavily未使用・track=Coding & Agentic Engineering等)
- **事故と修正**: Built With欄に注釈行が誤ペーストされ異常タグ2個が混入 → Owner修正 → 再fetchで正常10タグ確認

### Zenn記事(発信の第4弾)

- `zenn-articles/articles/runanchor-agent-receipt-verification.md`(type=tech・published:false)
- 切り口: 「関所自身を計量した」— evidence-only 64% vs full-gate 100%の36ポイント差が製品の存在理由、という軸。ハーネス自身の欠陥(ラベル漏洩・未配線・パース衛生)と限界を正直に書く構成
- **品質経路**: 別個体敵対レビュー(全数値を`bench-20261001-v4.json`/`.md`と突合)→4件修正 → natural-japaneseクイック(lint findings 0で収束) → Ownerプレビュー確認 → Webエディタで公開(Tech)
- 公開URL: https://zenn.dev/tatsuya7899/articles/ebd4a5c1e15b1e (記事冒頭コメントに記録済み)

## 学び・再発防止

1. **Devpostのタグ欄に注釈行を貼らない** — `form-answers.md`の欄記述に含まれる「(Long prose version…)」のような代替案注釈が、そのままフォームへ流れて異常タグ化した。転記用フォーム回答は「欄ごとに貼る値だけ」を単独で書くべき(`SUBMISSION_WORK_CHECKLIST`への追加候補)
2. **コスト記述は期間を明記する** — 「全期間$0.30」はv4分(見積+$0.4・未計上)を含まない表現だった。レビューで捕捉され「9/1〜10/1実測+見積未計上」と正確化。計測額は必ず期間と未計上分をセットで書く
3. **レビューの有効性が実証された** — Zenn記事の別個体レビューが数値全件突合で4件の実指摘(コスト精度・CLI列挙・漏洩経路・タイポ)を出した。外部発信物の「書いた人≠確かめる人」ゲートを継続する根拠になった

## 残っている未処理・期限

- `zenn-articles`に**未pushローカルコミット4件**(記事draft→URL→lint修正→公開URL記録)。あのrepoの規約でpushは人間のみ — Owner判断を待つ
- このファイル自体のpushは未実施(runanchor repoはpublic・push=承認制)
- ハッカソン結果発表: **2027年1月11日頃**(ルール記載)
- Zenn記事の公開後タスク: なし(プロジェクトページへの記事URL登録は任意)

## 次にやるなら(優先度順・未着手)

1. `zenn-articles`の4コミットをpushするか決める
2. X等での発信(記事・動画) — 未計画。やるなら即時検収ゲート
3. runanchorの拡張候補(bd/未着手メモ): oracleのピュアインタプリタマウント・per-op課金分解・計量モードの分母拡大
