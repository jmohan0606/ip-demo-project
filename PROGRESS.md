# PROGRESS

## Session 1 — 2026-07-03

### Section 0B: Route Reality Audit — COMPLETE

#### Step 1 — Backend enumeration & duplicate detection

The backend contains **two parallel families** implementing the same capabilities:

**Family A — "service family" (data-driven, real logic).** Thin facades in `app/services/*`
over real modules. Computes from CSV seed data (`tigergraph/sample_data/`, 51 files from the
old 42-vertex build), persists artifacts, and writes TigerGraph lineage via `*_linker.py`
modules:

| Capability | Router | Facade | Real module | Verdict |
|---|---|---|---|---|
| Feature store | `/features` | feature_store_service | `app/feature_store/` — aggregates advisor/txn/CRM/AGP CSVs into feature vectors | REAL |
| Embeddings/similarity | `/embeddings` | embedding_similarity_service | `app/embeddings/` — networkx degree/pagerank/neighborhood-hash embeddings + cosine similarity engine | REAL |
| Predictions | `/predictions` | prediction_service | `app/prediction/` — sklearn RandomForest over feature matrix, feature contributions, labels | REAL (synthetic training target is a rank heuristic — acceptable, revisit in Phase 7) |
| Opportunities | `/opportunities` | opportunity_service | `app/opportunities/` — scored detection from feature repo rows, evidence strings, priority model | REAL |
| Recommendations | `/recommendations` | recommendation_service | `app/recommendations/` (repository, tigergraph linker, playbook_selector, compliance_validator) | REAL but **BROKEN** — see defects |
| Feedback/learning | `/feedback-learning` | feedback_learning_service | `app/feedback/` — learning signal engine, reward engine, repository, linker; writes memory via MemoryService | REAL |
| Memory | `/memory` | memory_service + context_service | `app/graph/memory/` — ContextMemory/ConversationTurn/ReasoningTrace repos + linker | REAL |
| Knowledge/RAG | `/knowledge` | knowledge_management_service | `app/knowledge/` (parser, chunker, embedder, vector store, catalog, linker) | REAL |
| Insights/coaching | `/insights-coaching` | insights_coaching_service | `app/ai/insights/` — data collector, generation engine, repository, linker | REAL |
| AI chat | `/ai-chat` | ai_assistant_chat_service | `app/ai/chat/` — context assembler, chat engine, repository; saves conversation turns to memory | REAL |
| Agentic AI | `/agentic-ai` | agentic_ai_service | `app/agents/` — advisor coaching agent graph, registry, state, returns answer/confidence/tasks/evidence/reasoning_steps | REAL |

**Family B — "runtime family" (self-seeded demo data; the later "UI integration" build).**
Exposed at `/*-runtime` and `/{llm,tigergraph}-activation`:

| Router | Module | Problem |
|---|---|---|
| `/feature-runtime` | `app/features/` | `_seed_demo_vectors()` hardcodes 3 advisors; `FeatureEngineeringService.build_advisor_features` fabricates numbers from a persona multiplier; `PredictionRuntime` is fixed formulas with hardcoded confidences (0.86/0.79) |
| `/memory-runtime` | `app/memory/` | `_seed_demo_memories()` hardcodes 4 memories; simpler model than Family A |
| `/recommendation-runtime` | `app/recommendations/recommendation_runtime.py` + `opportunity_engine.py`/`recommendation_engine.py`/`learning_engine.py`/`learning_store.py`/`compliance.py` in same package | Templated recs keyed off opportunity-ID prefixes (`OPP-MANAGED` → fixed text) |
| `/knowledge-runtime` | `app/knowledge/knowledge_runtime.py` + chroma_adapter/chunker/mock_vector_store | Not hardcoded (chroma-or-mock vector store) but redundant with Family A knowledge |
| `/graph-runtime` | `app/graph/graph_runtime.py` | MCP→REST→mock ladder; adapter logic is real and partially reusable |
| `/tigergraph-activation`, `/graph-access`, `/tigergraph-foundation` | `app/graph/*` | Three more overlapping graph-access surfaces |
| `/llm-activation` | `app/llm/llm_runtime.py` + `app/agents/ai_assistant_runtime.py` | Azure-first-with-mock-fallback runtime; duplicates `app/ai/adapters/` (ModelAdapterFactory: openai/smartsdk/mock) |

**Fake aggregator layer (worst offenders):**
- `/ui-remediation/*` (`app/api/routers/ui_remediation.py`) — pure hardcoded response dicts.
- `/ui-integrated/*` (`app/services/ui_integrated_service.py`, `ui_integrated_expanded_service.py`)
  — same defect wearing a suit: persona-multiplier-fabricated KPIs and **fake agent traces**
  (fabricated durations/tool calls).

**Defects found during audit:**
1. **Backend cannot boot**: SyntaxError in 4 files (`app/api/main.py`,
   `app/orchestration/tools.py`, `app/services/ui_integrated_service.py`,
   `app/services/ui_integrated_expanded_service.py`) — imports placed above
   `from __future__ import annotations`. Merge artifacts. Fixed in this session (import
   reorder) so the tree is at least importable.
2. **`/recommendations/run` crashes by construction**: `RecommendationService` calls
   `engine.generate(entity_id, min_score, limit)` but the only `RecommendationEngine.generate`
   in the package takes `(opportunities: list[Opportunity])` — the runtime family overwrote the
   service family's engine file. The data-driven recommendation engine must be rebuilt in
   Phase 8 (consuming `app/opportunities` records + playbook_selector + compliance_validator,
   which survive intact).
3. **Orphaned frontend API modules**: `frontend/lib/api/dashboard.ts` → `/ui/executive-dashboard`
   and `advisor360.ts` → `/ui/advisor-360` — no such routes exist in any router.
4. `app/orchestration` engine (supervisor/agent sequencing is real) has its `ToolRuntime`
   wired to the fake `ui_integrated` data and runtime-family singletons — needs rewiring to
   Family A services.

#### Step 2 — Duplicate resolutions (winner → loser)

| Capability | KEEP | DELETE | Reasoning |
|---|---|---|---|
| Features | `app/feature_store/` + `/features` | `app/features/` + `/feature-runtime` | Winner computes from seed CSVs with lineage-capable structure; loser fabricates values from hardcoded seeds/multipliers (the #1 audit defect of the old build) |
| Predictions | `app/prediction/` + `/predictions` | `app/features/prediction_runtime.py` | sklearn models w/ feature contributions vs fixed formulas + hardcoded confidence |
| Embeddings/similarity | `app/embeddings/` + `/embeddings` | `app/features/similarity.py` | Graph-structure embeddings + typed similarity matches vs cosine over fabricated dicts with a canned explanation string |
| Memory | `app/graph/memory/` + `/memory` | `app/memory/` + `/memory-runtime` | Richer model (reasoning traces, conversation turns), repo+linker persistence vs seeded demo memories |
| Knowledge | `app/knowledge/` Family-A files + `/knowledge` | `knowledge_runtime.py` path + `/knowledge-runtime` | Parser/catalog/linker pipeline is more complete; chroma_adapter/chunker may be merged in where superior to `chunking.py`/`vector_store.py` (decide during Phase 5-6 when consolidating) |
| Recommendations | `app/recommendations/` repo/linker/playbook/compliance_validator + `/recommendations` | `recommendation_runtime.py`, runtime-family `opportunity_engine.py`/`learning_engine.py`/`learning_store.py`/`compliance.py`; rebuild `recommendation_engine.py` | Repository/linker are sound; engine was clobbered (defect #2) and will be rebuilt data-driven in Phase 8 |
| Feedback/learning | `app/feedback/` + `/feedback-learning` | runtime-family learning_engine/learning_store | Full signal/reward/outcome model + memory writes |
| LLM | consolidate BOTH into new `app/llm/client.py` `LLMClient` protocol (Section 2): mock/claude/real | `app/ai/adapters/` factory AND current `app/llm/llm_runtime.py` as-is | Neither matches the mandated adapter pattern; the richer interface (generate/generate_json/embed) informs the new protocol; `ClaudeLLMClient` added per CLAUDE.md |
| Graph access | consolidate into new `app/graph/client.py` `GraphClient` protocol; port foundation package's `tigergraph_client.py`/ingestion services as `RealGraphClient` backing; CSV loader backs `MockGraphClient` | `/graph-access`, `/graph-runtime`, `/tigergraph-activation`, `/tigergraph-foundation` surfaces collapse into one | Four overlapping access layers → one adapter pair per Section 2/3. Reusable pieces: `tigergraph_rest_adapter.py`, `mock_graph_data_service.py` (CSV-driven), MCP clients only if spec's MCP-first requirement survives GraphClient design |
| Fake aggregators | — | `/ui-remediation/*` (now), `/ui-integrated/*` (as each dependent page is rebuilt in Phase 10) | Non-negotiable FOUND-005: no hardcoded response dicts. `/ui-integrated` retained temporarily only because 10 workspace components currently render from it; each page rebuild removes its dependency, then the router+services get deleted |
| Legacy self-audit scaffolding | — | `app/audit/`, `app/hardening/`, `app/runtime_validation/` + routers `/final-audit`, `/deep-hardening`, `/runtime-validation`, plus `/demo-run`, `/demo-data` | They grade the *previous* build's "parts" and import `app.ui` (Streamlit); not part of the 32-page product. Delete with Phase 1 |

#### Steps 3+4 — Frontend route enumeration & classification

API client base: `frontend/lib/api/client.ts` → `NEXT_PUBLIC_API_BASE_URL` (default
`127.0.0.1:8000`). **Zero frontend references exist to the Family-A endpoints**
(`/features`, `/embeddings`, `/predictions`, `/opportunities`, `/recommendations`,
`/feedback-learning`, `/memory`, `/knowledge`) — the entire real pipeline is dark to the UI.

16 nav routes (`frontend/lib/navigation.ts`) + 10 hidden routes (`page.tsx` with no nav entry):

| Route | In nav | Renders | Calls | Class | Action |
|---|---|---|---|---|---|
| /dashboard | ✓ | remediation/dense-ui | /ui-remediation/* | (d) | Build real command-center pages (Exec/DDW/RDW/MDW) on Family A + AGP/CRM modules |
| /revenue-analytics | ✓ | dense-ui | /ui-remediation | (d) | Build real (Revenue Intelligence blueprint) |
| /advisor-360 | ✓ | dense-ui | /ui-remediation | (d) | Build real Advisor 360 (pipeline page, Phase 10 first) |
| /agp | ✓ | agp-workspace | **nothing** (hardcoded JSX) | (d) | Build real against new `app/agp/` (Phase 4) |
| /what-if | ✓ | whatif-simulator-client | client-side formula + /ui-integrated/what-if/run | (d) | Rebuild against `/predictions` scenario scoring |
| /predictions | ✓ | prediction-workspace | `predictions_workspace.ts` = **client-side hardcoded arrays** | (c) | Rewire to real `/predictions` API |
| /recommendations | ✓ | dense-ui | /ui-remediation | (c) | Rebuild against `/opportunities`+`/recommendations`+`/feedback-learning` (after engine fix) |
| /recommendation-roi | ✓ | roi workspace | nothing (hardcoded) | (d) | Build real from feedback/outcome/learning-signal data |
| /ai-assistant | ✓ | ai-assistant-workspace | `/ai-chat/ask` + endpoints.ts (`/agentic-ai/run`) | (b~a) | REAL backend — keep, restyle, verify e2e |
| /knowledge | ✓ | knowledge-workspace | /ui-integrated (fake) | (c) | Rewire to real `/knowledge` search/ingest |
| /graph-explorer | ✓ | dense-ui | /ui-remediation | (c/d) | Rebuild against GraphClient-backed explorer API |
| /features-embeddings | ✓ | dense-ui | /ui-remediation | (c) | Rebuild against real `/features` + `/embeddings` (Feature/Embedding Lab pipeline pages) |
| /memory-explainability | ✓ | dense-ui | /ui-remediation | (c) | Rebuild against real `/memory` (memories, turns, reasoning traces) |
| /agents | ✓ | observability workspace | `observability.ts` (hardcoded) | (d) | Build real from `/orchestration/run` traces once ToolRuntime is rewired |
| /data-ingestion | ✓ | dense-ui | /ui-remediation | (c) | Section 3B: Data Health page over ported foundation-package ingestion APIs |
| /admin | ✓ | admin-health-workspace | nothing (hardcoded) | (d) | Build real over /health, /config/status, adapter status |
| /feature-runtime | ✗ | feature-runtime-workspace | /feature-runtime (losing family) | delete | Superseded by rebuilt Feature Lab |
| /graph-runtime | ✗ | graph-runtime-workspace | /graph-runtime | delete | Folded into Graph Explorer + Admin health |
| /knowledge-runtime | ✗ | knowledge-runtime-workspace | /knowledge-runtime | delete | Superseded by rebuilt Knowledge page |
| /memory-runtime | ✗ | memory-runtime-workspace | /memory-runtime | delete | Superseded by rebuilt Memory/Explainability page |
| /recommendation-runtime | ✗ | recommendation-runtime-workspace | /recommendation-runtime | delete | Superseded by rebuilt Recommendations page |
| /orchestration | ✗ | orchestration-workspace | /orchestration/run | (b) | Real engine — keep concept; becomes part of Agent Observability page after ToolRuntime rewire |
| /llm-activation | ✗ | llm-activation-workspace | /llm-activation | delete | Replaced by LLMClient status in Admin page |
| /tigergraph-activation | ✗ | tigergraph-activation-workspace | /tigergraph-activation | delete | Replaced by GraphClient status in Admin/Data Health |
| /document-ingestion | ✗ | document-ingestion-workspace | /ui-integrated/documents/ingest | (c) | Rewire to real `/knowledge` ingest; merge into Knowledge or Data Health page |
| (none) | — | — | — | (e) | **Agentic reasoning console** (confidence/evidence/reasoning-steps at Streamlit depth): `/agentic-ai/run` returns the payload; only a Q&A box uses it today. Build Explainability/AI-Assistant page exposing full trace (Phase 10) |

#### Step 5 — Deletions performed this session

- `frontend/components/remediation/` (dense-ui.tsx) — deleted; the 8 nav routes that rendered
  it now render an honest "page pending rebuild" placeholder (no fake data) until their real
  builds in Phases 10-11.
- `app/api/routers/ui_remediation.py` + registration in `app/api/main.py` — deleted.
- `frontend/lib/api/ui-remediation.ts` — deleted.
- Import-order SyntaxErrors fixed in the 4 files listed above (backend now compiles).

**Streamlit safety check (required before Phase 1):** `app/ui/` (1,376 lines) imports only
`app.agents`, `app.config`, `app.ingestion`, `app.models`, `app.services` — every capability
it renders has an API route in Family A. The agentic console depth (reasoning/evidence/
confidence) exists at `/agentic-ai/run` (classification (e) above covers its missing page).
Nothing lives only in Streamlit. Safe to delete in Phase 1. Note: `app/audit`,
`app/hardening/audits/ui_progress_auditor.py`, `app/runtime_validation` reference `app.ui`
and are deleted along with it (see scaffolding decision).

### Seed data note

`tigergraph/sample_data/` (51 CSVs, old 42-vertex model) is what Family A currently reads.
The foundation package (`docs/tigergraph_foundation/data/sample/`, 182 CSVs, 56-vertex model)
supersedes it per Section 3. Phase 3 will repoint the CSV loading path at the foundation
package data via `MockGraphClient`; `tigergraph/{schema,loading,queries_v1,queries_v2}` at
repo root are the OLD graph assets and are superseded by the foundation package's
`tigergraph/` tree.

### Phase 1: Foundation (Streamlit removal + adapter pattern) — COMPLETE

- Deleted `app/ui/` (Streamlit, 1,376 lines) and removed `streamlit` + `plotly` (Streamlit-only)
  from `pyproject.toml`; added `anthropic` + `httpx`; fixed setuptools flat-layout config.
- Deleted legacy self-audit scaffolding per 0B decision: `app/audit/`, `app/hardening/`,
  `app/runtime_validation/`, routers `/final-audit`, `/deep-hardening`, `/runtime-validation`,
  `/demo-run`, `/demo-data`, their service facades, `app/orchestration/demo_orchestrator.py`,
  and the stale tests that exercised them. Frontend `endpoints.ts` cleaned of dead routes.
- **Adapter pattern (Section 2) built and verified:**
  - `app/graph/foundation_store.py` — `FoundationGraphStore` loads the foundation package's
    182 CSVs via `data/manifest.json` into typed vertex/edge indexes with out/in traversal
    helpers. Verified: 56 vertex types, 126 edge types, 24,031 + 85,297 = 109,328 rows,
    zero manifest row-count mismatches, ~1.7s load.
  - `app/graph/client.py` — `GraphClient` Protocol; `RealGraphClient` (httpx RESTPP, ported
    from the foundation package client, serves both local_real and real modes);
    `MockGraphClient` (same envelope, backed by the store, `MOCK_QUERY_IMPLS` registry +
    `@mock_query` decorator for Phase 3 GQ implementations); `get_graph_client()` selected by
    `GRAPH_CLIENT_MODE`.
  - `app/llm/client.py` — `LLMClient` Protocol; shared `_render_messages` so identical
    system/user content reaches all three backends; `MockLLMClient` (deterministic),
    `ClaudeLLMClient` (anthropic SDK, default `claude-haiku-4-5-20251001`), `RealLLMClient`
    (Azure OpenAI); `get_llm_client()` selected by `LLM_CLIENT_MODE`. SDK imports live only
    inside their respective classes.
  - `.env.example` (mock/mock defaults); `.env` remains user-provided and gitignored.
  - `/adapters/status` endpoint reports active modes (verified live over HTTP).
- Settings extended: GRAPH_CLIENT_MODE, LLM_CLIENT_MODE, TIGERGRAPH_RESTPP_URL,
  ANTHROPIC_API_KEY/MODEL, AZURE_OPENAI_*, FOUNDATION_DIR.

### Phase 3: Data access layer — COMPLETE (mock side; live install in progress)

All 43 GQ-### catalog queries implemented as Python equivalents for MockGraphClient
(`app/graph/queries/`), mirroring GSQL traversals and PRINT output keys, RESTPP-style vertex
envelopes. Verified with `scripts/verify_mock_queries.py` against the package's own 43-case
contract: 43/43 execute, 0 hard failures. 3 empty-required results are data-truthful, not
bugs: U_EXEC has no notifications in the data; the GQ-038 case's scenario_type
`AGP_ACTIVITY_IMPROVEMENT` doesn't exist in the data (only `AGP_CRM_IMPROVEMENT` — package-
internal inconsistency to report upstream); GQ-043 correctly finds 0 issues in a
verified-clean graph.

### Phase 2: Local TigerGraph (Docker Community Edition 4.2.3) — schema+jobs installed, load in progress

Container up on this 2-core/8GB codespace (all 16 services Online). **Two real-engine
incompatibilities found that static validation could not catch** (the whole point of doing
this early):
1. `gsql -f` rejects the trailing `;` after `WITH primary_id_as_attribute=...` /
   `WITH REVERSE_EDGE=...` DDL clauses → fixed mechanically (strip trailing semicolons);
   all 56 vertices + 126 edges + graph created successfully.
2. All 182 loading jobs fail semantic check as shipped: `USING HEADER="true"` with `$"col"`
   references requires an initialized `DEFINE FILENAME` → fixed mechanically (initialize
   each FILENAME to the container CSV path); all 182 jobs then compile. Both fixes need to
   go back into the foundation package + its validators (report upstream).
Data load via `RUN LOADING JOB` running in background. 43 query INSTALL (C++ compile) still
pending — slow on 2 cores; will run after load completes.

### Phases 4-9: Full AI pipeline — COMPLETE and verified end-to-end (mock mode)

- **Phase 4** `app/agp/` + `app/crm/`: real domain logic per AGP-001..006 / CRM-001..005,
  over GraphClient only. AGP-004 on/off-track score preserves components + explanation.
- **Phase 5** `app/features/engineering.py`: 33 Feature_Catalog features with per-feature
  lineage (source query + evidence ids); versioned snapshot persisted to SQLite AND as
  phx_dm_feature_snapshot vertex + edge.
- **Phase 6** `app/embeddings/service.py`: deterministic versioned feature-projection
  (spec Section 10 wording followed; labeled a simulation), 60 advisors, 300 similarity
  matches persisted with reason features.
- **Phase 7** `app/prediction/service.py`: REVENUE_DECLINE_RISK + AGP_OFF_TRACK_RISK with
  transparent contributions, confidence, severity bands, persisted reasoning traces.
- **Phase 8** `app/opportunities/service.py` (4 rules, severity composed 25/25/20/15/15 per
  spec Section 7) + `app/recommendations/service.py` (playbook-mapped actions, ranked by
  base score x learned family weight; rebuilt after the 0B clobbered-engine finding).
- **Phase 9** `app/feedback/service.py`: feedback actions persist feedback → outcome →
  learning-signal artifacts and move the family weight read at ranking time.
  **Verified: two feedback rounds flip the ranking order** (CRM_EXECUTION 65.4→54.9 w=0.84
  vs MANAGED_MIX 49.5→59.4 w=1.2). GQ-029 traces the complete chain for A001:
  recommendation → opportunity → feature snapshot → playbook → reasoning → feedback →
  outcome → learning. Routers rewired; verified over HTTP.

Completed: 0B; Phases 1, 3(mock), 4, 5, 6, 7, 8, 9. Pipeline demo core works end-to-end.
In progress: Phase 2 TigerGraph data load (background); query INSTALL pending.
Known issues / deferred: runtime-family modules (app/features old files, app/memory,
*-runtime routers) still present — consolidation sweep planned with Phase 10 page rebuilds;
`/ui-integrated/*` + orchestration ToolRuntime rewire pending Phase 10; foundation-package
GSQL fixes need upstreaming; LLMClient not yet consumed by insight/chat services (Phase 10
AI pages will wire it).
Next: 1) finish TigerGraph load + install 43 queries + run query cases (local_real);
2) Phase 10 — design system tokens/primitives, then pipeline pages; 3) consolidation sweep.

## Session 2 — 2026-07-03 — Live API chain verification (real curl output, advisor A001/A020)

Verification demanded concrete proof, not status claims. All commands run against a live
`uvicorn app.api.main:app` (GRAPH_CLIENT_MODE=mock, 109,328 rows). Every stage links to the
previous stage's real output IDs:

- **STEP 1 feature engineering** — `POST /features/compute/A001` → snapshot `FS_A001_20260703_v2.0`,
  33 features. `managed_revenue_ratio=0.1123` lineage = GQ-006, `43474.27/387293.22`, product
  ids [P001,P002,P049,P050]. REAL, math checks.
- **STEP 2 predictions** — `POST /predictions/run/A001` → PRED_REVDECL (16.7) + PRED_AGPRISK
  (25.8), both cite `feature_snapshot_id: FS_A001_20260703_v2.0` (matches Step 1); every
  contribution's `value` equals the Step-1 feature value (peer_gap -41.78, overdue 3,
  kpi_on_track 0.275). REAL, linked.
- **STEP 3 opportunities** — `POST /opportunities/detect/A001` → OPP_PIPELINE (65.4) +
  OPP_MANAGEDMIX (49.5), same snapshot. A001 is a healthy advisor (pred scores <40) so the
  two prediction-derived rules correctly did NOT fire (`derived_from_prediction: None`); the
  two feature-driven rules did. OPP_MANAGEDMIX impact $55,235.76 = 387293.22×(0.35-0.1123)×0.6.
  Honest: for A001 this link is None by design.
- **PREDICTION→OPPORTUNITY link proven separately** on at-risk advisors: A015/A020 produce
  OPP_AGPRESCUE with `derived_from_prediction: PRED_AGPRISK_A0xx`. A020: AGP pred score 56.8
  (≥40) → OPP_AGPRESCUE_A020 → REC_OPP_AGPRESCUE_A020 `based_on PRED_AGPRISK_A020_v2.0`.
  The link is live, not dead — it fires when the score crosses threshold.
- **STEP 4 recommendations** — `POST /recommendations/generate/A001`: learned weights already
  re-ordered output — MANAGED_MIX (49.5×1.25=61.9) outranks CRM_EXECUTION (65.4×0.84=54.9)
  despite lower base. Each rec links to its Step-3 opportunity_id.
- **STEP 5 evidence** — `GET /explainability/recommendation/REC_OPP_MANAGEDMIX_A001_v2.0`:
  chain recommendation→opportunity→FS_A001_20260703_v2.0→PB001→reasoning; reasoning trace
  records applied weight 1.25 and base→adjusted 49.5→61.9.
- **STEP 6 feedback loop (the centerpiece) — PROVEN** via real HTTP:
  BEFORE weights {CRM 0.84, MANAGED 1.25}, order [MANAGED_MIX 61.9, CRM_EXECUTION 54.9].
  3× COMPLETE on CRM (0.84→1.14) + 3× REJECT on MANAGED (1.25→1.01).
  AFTER weights {CRM 1.14, MANAGED 1.01}, order [CRM_EXECUTION 74.6, MANAGED_MIX 50.0].
  **Ranking flipped as a direct result of feedback.** Loop is closed and live.

Verification-pass housekeeping: all 11 claimed commits present; foundation validators 4/4 PASS;
verify_mock_queries 43/43 0 failures; frontend tsc+build green; deleted modules have 0 tracked
files (removed leftover .pyc cruft); .env safe (only .example tracked, 0 leaked keys).
FLAG (not a false claim): runtime SQLite DBs are git-tracked (data/feature_store/*.db,
data/sqlite/*.db) — hygiene smell, verification runs mutate them; consider gitignoring.

## Session 2 (cont.) — Phase 2 TigerGraph live re-verification (in progress)

Resumed the live load. Progress: schema (56V/126E) + 182 jobs installed; vertex load advanced
40 -> 51/56 types (23,521 rows) after running the QUOTE-fixed jobs for the 16 previously-empty
JSON-column types.

**4th real-engine finding (isolated by controlled single-row tests):** TigerGraph 4.2.3 GSQL
file-loader with `QUOTE="double"` fails on any field that contains BOTH a doubled-quote escape
(`""`) AND the separator comma inside that quoted field. Confirmed by binary search:
  - plain string + date-only DATETIME .......... loads OK
  - `""`-JSON, NO internal comma + date-only .... loads OK
  - `""`-JSON WITH internal comma .............. 0 objects, "Invalid Attributes" (column shift)
Root cause: the tokenizer mis-splits on the internal comma, shifting subsequent columns so the
DATETIME attribute receives JSON text -> whole row rejected. Affects exactly the 5 vertex types
whose JSON columns hold arrays/objects with internal commas: reasoning_trace, similarity_match,
learning_signal, coaching_session, simulation_scenario. (crm_activity loaded fine: its
comma-bearing free-text column has no `""`.) Report upstream alongside findings 1-3.
Correct production path is RESTPP JSON upsert (the foundation package's real ingestion service,
and our RealGraphClient.upsert), which bypasses the CSV tokenizer entirely.
