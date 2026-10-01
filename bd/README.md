# bd/ — design history (日本語・English)

このディレクトリは設計の作業記録(前提整理・要件/設計/タスク仕様・敵対的レビュー・セッション引継ぎ)を保持します。本文はプロジェクト規約により**日本語**、各文書の冒頭に **English summary** を併記しています。

This directory holds the project's working design record: premises,
requirements/design/tasks specs, adversarial reviews, and the session
handoff. The files are in **Japanese** by project convention — internal
documents stay in the author's working language; submission artifacts are
English.

We keep them public on purpose: the process — including the hypotheses,
the review findings, and what was retracted — is part of the artifact.

| file | contents |
|---|---|
| `IDEA-runanchor_premises.md` | 前提整理 — where the idea came from, what we assumed |
| `IDEA-runanchor_dtf.md` | earlier framing exploration |
| `SPEC-runanchor_requirements.md` | requirements (what the gate must do) |
| `SPEC-runanchor_design.md` | design (how receipts/verify/oracle work) |
| `SPEC-runanchor_tasks.md` | task breakdown |
| `review-*_runanchor_*.md` | adversarial review results + fixes |
| `SESSION-HANDOFF-runanchor_20260929.md` | session handoff log |

The measured results themselves are English: `eval/bench-*.md`.
