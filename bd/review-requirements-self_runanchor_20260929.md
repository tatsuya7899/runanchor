# 要件段レビュー記録 — SPEC-runanchor_requirements(段1)

> **English summary**: Stage-1 (requirements) review record — self-review
> under a separated create/verify procedure after the review-agent quota
> was exhausted; the stage-2 mandatory gate covered the requirements
> document as well. The fallback and its reasoning are logged.

**日付**: 2026-09-29 / **方式**: **セルフレビュー(作成と検証の分離手順)** — Plan agent委任を試みたがサブエージェント週次クォータ枯渇(trace 0ebe41951e55bae133cde6c22fb07e50)のため、Studio規約のcloudフォールバック(作成者と別手順での検証)で代替。**独立レビューとしては段2(設計)の必須ゲートで代替される**(段2レビューは要件書も対象に含まれる)。
**判定**: 追補(P0×0 / P1×1 / P2×3) → 全件反映済み

## 観点と発見

### ① 受入シナリオのテスト翻訳可能性
- シナリオ2「テスト実行の証拠」・シナリオ7「一通り操作」は機械判定可能だが表現がやや軟い(P2) → FR-2に「実行ログ参照またはその断片」を明記して補強
- 残り7件はそのままテスト化可能

### ② スコープ外の粒度
- 抜け3件(P2): エージェント能力の高度化(最低ループ超)・撒き種コーパスの網羅・他者receipt相互運用 → 追記済み

### ③ [要確認]の誤魔化し
- なし。4件は全て人間裁定と一致した形でFR/成功基準/スコープ外へ反映済み(機械検品 `^- \[要確認\]`=0)

### ④ premisesとの整合 — **P1×1**
- **FR-1/FR-2(全検収書に外部実行記録への参照) vs FR-6(外部接続なしで同じ流れ)の矛盾**: デモモードでは実アンカーが存在しないのに要件は参照を必須としていた → FR-6へ「デモ検収書はfixtureアンカーを持ち『デモ由来』を区別表示(実記録と偽装しない)」を追記して解消。sagi-shieldの「DEMOバッジ」先例に倣う
- 軽微(P2): FR-2がpremises記載の検収書項目から「モデル・シード」を欠落 → 追記済み(実行条件として)
- 整合済みの確認: premises計量の「判定主体(人/機械)」→要件は機械のみ。Gate 0宿題③「人条件は探索的・MSCは機械条件のみ」と一致するため矛盾なし

## 残置

- premises側のMVP表に旧名 `agent-receipt` の記述が残存(改名後のrunanchorに統一すべき・premises文書の軽微な陳腐化。要件書側は正しい)
