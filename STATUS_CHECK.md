# Status Check — 2026-07-05 — OpportunityService zero/empty bug: does it degrade live output?

Verified before deferring the repoint, against the same evidence bar as the rest of the build
(real HTTP calls, real advisor figures, before/after). **Verdict: the bug reaches user-visible
output on the CHAT page — so it was NOT deferred; the repoint was done now. The AGENTIC page was
never affected.**

## Method

Traced how the legacy `app/services/opportunity_service.py` output flows to each page, then ran
real endpoints for A001 and A020 (`GRAPH_CLIENT_MODE=mock`, `LLM_CLIENT_MODE=mock`, 109,328 rows).

## Findings per page

### Agentic page (`/agentic-ai/run`) — NOT affected
- `app/agents/tools/service_tools.py` **imported** the legacy `OpportunityService` (line 17) but
  **never called it** — a dead import. The toolbox's `run_opportunities` uses the real Phase-8
  `OpportunityDetectionService.detect_for_advisor` (returns A001 65.4/49.5, A020 74.8/68.1/56.8).
- So the zero/empty legacy bug **cannot** reach agentic output. Confirmed by inspection + a live
  run (A020: confidence 0.85, 5 tasks, real answer, 0 errors).
- Action taken: removed the dead legacy import (+ two unused request-model imports) for hygiene —
  **no behavior change**.

### Chat page (`/ai-chat/ask`) — WAS degraded (bug reaches visible output)
- `app/ai/chat/context_assembler.py` **did call** the legacy
  `OpportunityService.list_opportunities(entity_id)`, which reads an **unpopulated** SQLite repo
  and returned **0 rows** for every advisor. (Note: the operative mechanism here is the empty
  repo-backed read, not literally `FeatureStoreService` zeroing — chat only reads, never writes.)
- **BEFORE (real HTTP):** for a question literally asking *"What are my top opportunities and
  their revenue impact?"*, the assembled chat context contained **0 opportunity items** for both
  A001 and A020 (context sources were only Context-Memory / Knowledge-RAG / Insights). The real
  pipeline meanwhile has 2 (A001) / 3 (A020) real opportunities. The chat answer to an
  opportunity question was grounded in everything *except* the real opportunities — a demonstrable
  visible degradation, not merely an internal tool result.

## Fix (chat repoint — done now, ADV0001-standard before/after)

Repointed `context_assembler` off the legacy `OpportunityService` onto the real
`OpportunityDetectionService.detect_for_advisor(entity_id)` (guarded to Advisor scope), mapping
`opportunity_type→title`, `impact_summary→content`, `score→score`.

| Advisor | BEFORE opp-context items | AFTER opp-context items (real Phase-8) |
|---|---|---|
| A001 | 0 | 2 — CRM_EXECUTION **65.4** ($405k pipeline / $324k weighted, 3 overdue), ADVISOR_GROWTH **49.5** (managed 11.2% vs 35%) |
| A020 | 0 | 3 — AGP_MILESTONE **74.8** (off-track 56.8/100), CRM_EXECUTION **68.1** ($1.05M pipeline / $642.5k weighted), ADVISOR_GROWTH **56.8** (managed 15.1% vs 35%) |

AFTER figures match `OpportunityDetectionService` exactly. The visible A020 answer now surfaces
the real opportunity ("AGP off-track risk scored 56.8/100 … recover attainment").

## Verification

- Backend imports OK; live server came up; **36 app routes** (unchanged — no routers touched).
- Chat before/after captured over real HTTP (0 → 2 for A001, 0 → 3 for A020, real figures).
- Agentic live run post-change: 0.85 confidence, 5 tasks, real answer, 0 errors (no regression).
- Frontend `tsc --noEmit`: PASS (change is backend-only; no frontend files touched).

## Remaining state

- Legacy `app/services/opportunity_service.py` now has **one** consumer left: the
  `app/services/recommendation_service.py` facade. Full deletion is still gated on that facade
  (itself legacy) being repointed/removed — a separate, scoped follow-up, not this fix.

---

# Final Closure Pass — 2026-07-05

## PART A — Repoint recommendation_service facade + delete opportunity_service — DONE

- **Finding:** the facade `app/services/recommendation_service.py` used the legacy
  `OpportunityService` only inside `run_recommendations`, which was already **broken/dead**: it
  called `RecommendationEngine.generate(entity_id, min, limit)` but the real signature is
  `generate(opportunities)` → **TypeError by construction**. Not reachable from any router;
  `feedback_learning_service` uses only `update_status`/`repo`, `context_assembler` only
  `list_recommendations`, and `service_tools`'s facade import is dead (uses the real pipeline).
- **Fix (same pattern as the chat-context repoint):** `run_recommendations` now delegates to the
  real Phase-8 `app.recommendations.service.RecommendationService.generate_for_advisor`, which
  internally detects opportunities via the real `OpportunityDetectionService` and persists the
  full lineage chain. Dropped the `OpportunityService`, `RecommendationEngine`, and
  `TigerGraphRecommendationLinker` usages from the facade.
- **Before/after (real):**
  - BEFORE: `run_recommendations(A001)` → `TypeError: RecommendationEngine.generate() takes 2
    positional arguments but 4 were given`.
  - AFTER: A001 → completed, **2** recs (REC_OPP_PIPELINE 74.6, REC_OPP_MANAGEDMIX 50.0);
    A020 → completed, **3** recs (REC_OPP_AGPRESCUE 85.3, REC_OPP_PIPELINE 77.6,
    REC_OPP_MANAGEDMIX 57.4). Figures match the live `/recommendations` router output exactly.
- **Deletion:** confirmed `app/services/opportunity_service.py` now has **zero** live consumers
  (grep across `app/`), deleted it. Backend imports clean — 36 routes.
