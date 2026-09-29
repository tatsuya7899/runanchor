# レビュー依頼: runanchor 構造破壊分析(Gate 1)

あなたはこのプロジェクトの敵対的レビュアーです。**壊す側の立場**で読んでください。提案を守る・補強するのは依頼者の仕事です。あなたの仕事は崩れる箇所を特定することです。

## 対象(全てReadして引用せよ。引用なき指摘は無効)

- `/Users/tatsuyasasaki/Developer/_incubator/runanchor/bd/IDEA-runanchor_dtf.md` ← 審査対象
- `/Users/tatsuyasasaki/Developer/_incubator/runanchor/bd/IDEA-runanchor_premises.md` ← 入力(前提・先行技術・リスク)
- `/Users/tatsuyasasaki/Developer/_incubator/runanchor/bd/SPEC-runanchor_requirements.md` ← 参照(確定済み要件との整合確認)

## 観点(Gate 1の確認項目)

1. **生態系モデル**: 「エージェント出力の検収」領域の構造を正しく捉えているか。抜けているアクター・力学はないか
2. **根源的バイアス**: B1〜B7に見落としはないか。特に「検証する側(runanchor自身)は正しい」という自案への向きのバイアスが十分か
3. **破壊レバー**: L1〜L4の選定は適切か。「関所の信頼性を誰が保証するか」をレバーにすべきではないか
4. **コンセプト群**: C1〜C6は十分に非連続か。既存の延長線上のものを外せ
5. **堀と墓場**: 墓場判定(「計量値が平凡なら転落する」)への対処は十分か。撒き種コーパスは本当に堀になるか
6. **有望コンセプト**: C1維持+示唆反映 vs C2(信用調査局)/C6(監査基盤)への振り切り — ハッカソン制約(締切10/30・$25・個人)下でどちらが正しいか

【ゲート照合】あなたは `~/.agents/skills/business-design/references/phase1-dtf.md` の
Gate 1節をReadし、確認項目を全項目照合せよ。成果物に該当項目の記載が無い場合は「未記載」として指摘する。

## 出力形式

- 各指摘は `要件破綻(P0) / 修正すべき(P1) / 改善余地(P2)` の3段で分類し、対象文の引用を1行添える
- 最後に総合判定を1行で: `通過 / 追補 / 差戻し(Phase 0へ)`
- 出力は `/Users/tatsuyasasaki/Developer/_incubator/runanchor/bd/review-dtf-result_20260929.md` 相当の内容として返す
