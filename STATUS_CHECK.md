# STATUS_CHECK — Section 11 COMPLETE

_Date 2026-07-06. Traced from PROGRESS.md, `git log`, and live verification — not memory._

## Headline

**All buildable subsections of Section 11 are complete** (11.1–11.8 + 11.11; 11.9/11.10 were
model-routing guidance / poster placement, satisfied). Every subsection shipped with real metrics,
honest quality gates, and real-Claude verification wherever AI *behavior* is claimed.

- **29 Section-11 commits this session**, all pushed. `origin/main` == `HEAD` == **120 commits**, 0 unpushed.
- Backend imports clean (**42 routes**); frontend `tsc --noEmit` exit 0; no binaries tracked (artifacts gitignored).
- **7 models registered, 5 serving** (2 correctly gated to fallback).
- **Section 10 remains deferred** — not started, per standing instruction.

## What shipped (real results)

| § | Deliverable | Real result |
|---|---|---|
| 11.1 | Real model tier (`ModelClient` adapter) | XGBoost revenue-decline promoted to the LIVE /predictions path with real TreeSHAP (ROC-AUC 0.7755); GRU forecast (sMAPE 0.081, beats seasonal-naive); GraphSAGE GNN (link-pred AUC 0.92); Isolation Forest anomaly (care-framed); model registry in Admin. Dormant synthetic-label RF retired. **2 of 6 models honestly gated → fallback** (agp-off-track 0.63, household-churn PR-AUC 0.012). |
| 11.2 | RL formalization | Verified feedback loop documented as a contextual bandit (state/action/reward/policy/update), surfaced above the weight-trajectory replay. |
| 11.3 | FL = Feedback Loop (NOT Federated Learning) | +144 outcome-variety rows (real success/failure mix incl. negative outcomes); contrastive GNN fine-tune (`graphsage-v1-ft`, AUC-retention-gated 0.969→0.953); live before/after retraining control with honest "small on demo-scale" note. |
| 11.4 | Temporal knowledge graph | Point-in-time feature snapshots (as-of date; A001 AUM $9.06M→$10.02M across dates); as-of graph traversal (19→13 nodes, AI artifacts hidden pre-2026); Memory Timeline temporal link. |
| 11.5 | Evaluation & Trust | Golden 25-Q set (20 grounded + 5 refusal); real-Claude harness (fails loudly in mock); **groundedness 85% / citation 100% / refusal 100% / 22-25 pass** (3 honest FAILs where Claude declined). Admin "Evaluation & Trust" tab. |
| 11.6 | Context engineering | RerankClient (local/cohere); scope-aware aggregate reasoning (real-Claude DDW division answer names 24 advisors, $14.7M, top + needs-attention — not one advisor); all 6 poster memory types populated; visible retrieve→rerank→prune trace on Explainability. |
| 11.7 | Observability | Per-LLM-call token/cost/latency (real from Claude response.usage; estimated for mock, flagged); Admin "Observability" tab. |
| 11.8 | MCP layer | feature_store + model_serving MCP tool families (6 tools); GET /mcp/tools + POST /mcp/invoke (verified live: model.similar_advisors → real GNN result). |
| 11.11 | Two AI Systems visible | "iPerform Insights and Coaching" (proactive) vs "iPerform Coach Q&A Assistant" (reactive) labeling; Model Strategy + AI Protections Admin tabs; business-outcome KPI mapping on Exec Dashboard. |
| 11.9 / 11.10 | Model routing / posters | Fable-designed items (11.1, 11.3, 11.5) delegated via general-purpose subagent with `model:"fable"`; 12 architecture posters already committed. |

## Honesty held throughout

- Deterministic / scorecard / graphsage-v1 / bandit fallbacks are never deleted — real mode falls
  back per-type via registry quality gates, so it can never regress the shipped behavior.
- No gate was tuned to pass: 2 XGBoost models + churn correctly do NOT serve; the eval shows 3
  genuine FAILs where Claude honestly declined partial answers (the hallucination guard working).
- Anchored advisor figures (A001 387,293.22 / A020 / firm F001 38,365,750.01) asserted intact on
  every training run and after the data expansion.
- Small effects (FL embedding separation, eval score) are shown truthfully with amber caveats, not massaged.

## Artifacts

- Full narrative: `PROGRESS.md` (Session 9 entries).
- Fable design docs: `docs/section11/11_1_model_design.md`, `11_3_fl_design.md`, `11_5_eval_design.md`.
- Eval runs (committed): `docs/section11/eval/` (golden set + real Claude runs + trend).
- QA screenshots: `docs/qa_screenshots/s11-*.png`.
- Trained artifacts: `models/artifacts/` (gitignored) + committed `models/registry.json`.

## Ops note (carry forward)

Run the backend CWD-independent to avoid the recurring empty-graph-store issue:
`env PYTHONPATH=/workspaces/ip-demo-project FOUNDATION_DIR=/workspaces/ip-demo-project/docs/tigergraph_foundation SQLITE_DB_PATH=/workspaces/ip-demo-project/data/feature_store/iperform_features.db uvicorn app.api.main:app --host 127.0.0.1 --port 8000`.
Set `LLM_CLIENT_MODE=claude` for any AI-behavior demo/verification; `MODEL_CLIENT_MODE=real` to serve the trained models.

## Closing verifications (2026-07-06, requested before final close)

### Registry reconciliation (7 registered vs "2 of 6")
The 7th registry entry is **`graphsage-v1-ft`** — the Section-11.3 outcome-driven fine-tune of the
GNN — NOT the retired dormant scorecard (that is a code-level fallback, never a registry entry). So
7 registered = the 6 base 11.1 models + `graphsage-v1-ft`; **5 serving**, 2 gated to fallback
(`agp-off-track-xgb` ROC-AUC 0.6347 < 0.65; `household-churn-xgb` PR-AUC 0.0117 < gate).

### 1. Advisor-level multi-turn continuity — RUN LIVE on real Claude (LLM_CLIENT_MODE=claude)
Distinct capability from the division-level test; run fresh, not inferred. Advisor A007:
- **Turn 1** — "What is this advisor's single biggest revenue risk right now?" → grounded answer
  (LTM revenue $470,497.69, 3-mo growth 17.83%, AGP goal attainment at risk).
- **Memory write CONFIRMED** — conversation memories for A007 went **0 → 1**; the newest conversation
  memory literally stores the turn-1 Q&A ("Q: What is this advisor's single biggest revenue risk… A:
  For Advisor A007… LTM revenue of $470,497.69…").
- **Turn 2 assembled context INCLUDES turn 1** — for the follow-up, the assembled `Context Memory`
  item contains: "- Conversation Memory: Q: What is this advisor's single biggest revenue risk right
  now? A: For Advisor A007… LTM revenue of $470,497.69 and strong 3-month growth of 17.83%, though AGP
  goal attainment…". Turn 1's memory is demonstrably in turn 2's context.
- **Turn 2 answer BUILDS on turn 1** — the follow-up "And what single action would most reduce **that
  risk**?" (never restating what the risk is) returned a concrete action (managed-account review of
  high-AUM/low-penetration households; RETENTION opportunity, revenue-decline risk 54.5/100, $64,105
  exposed) and explicitly noted "Relevant memory was used to preserve prior context." PASS.

### 2. RerankClient before/after — concrete ordering change on a real query
Diverse candidate set of one chunk from each of 6 distinct docs, with the relevant one deliberately
placed **last** in input order:
- **BEFORE (input order):** `reg_bi_suitability_manual.pdf` at position input[5] (last).
- **Query:** "What dollar threshold triggers supervisory principal review of a recommendation?"
- **AFTER rerank:** `reg_bi_suitability_manual.pdf` → **#1 (rerank 0.6696)**, far above the runner-up
  (client_review 0.4155); the least-relevant `market_outlook_2026_q3.pdf` sinks to last.
So the reranker measurably changes both **ordering** (last → first) and, under top-K pruning,
**selection** (the answer-bearing doc is now kept, not dropped). Not just "the adapter exists."

---
_Status: SECTION 11 COMPLETE — all subsections done + both closing verifications passed on real
Claude, committed and pushed to origin/main. Section 10 deferred._
