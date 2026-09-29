# runanchor — Submission Description (draft)

> 提出フォーム・READMEの「何を外に出すか」の正本。英語で書く。仮置き — Gate通過後に確定する。

## One-liner

CI checks the diff. Nothing checks the agent's *report*. runanchor issues a verifiable receipt for every agent run — anchored to the provider's own execution record (Token Factory Sandboxes operation UUID / image ID) — so "it works" becomes provable, not a confidence claim.

## Problem

Code generation got cheap; verification didn't. Review is now the bottleneck (Sonar State of Code 2026: 42% of committed code is AI-generated; 96% of devs don't fully trust it; 38% say reviewing AI code takes more effort than human code). Agent-run PRs pass normal CI — but CI only sees the final diff, never the run: which commands actually ran, which tests really passed, what the agent discarded.

## What it does

- `runanchor run "<task>"` — a coding agent (Nemotron via Token Factory) writes/runs/tests code inside a Token Factory Sandbox
- Every run emits a **receipt**: diff hash, test logs, exit codes, cost, model, seed, and the provider-issued operation UUID + image ID
- `runanchor verify <receipt>` — forks the recorded image, re-runs the command list, compares results. A false claim is physically detectable, not just suspicious
- A gate (human approve/reject, or machine reviewer for measurement mode) decides adoption. Rejected runs stay in the ledger with reasons

## Key numbers

{Headline metrics — VERIFYマーカー規約に従い各数値の直下にVERIFYマーカーを置く(globは~/Developer基準・`_incubator/runanchor/...`から書く)}

## Architecture

{決定論コア(receipt発行・verify・台帳)とLLM縁(エージェント駆動・機械レビュアー)の境界が読める図}

## What this does NOT prove

{ライブ未検証・合成データ天井・撒き種コーパスの偏りなど、測った層を名指す}
