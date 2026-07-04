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

## Session 2 (cont.) — Phase 2 FINAL STATUS (hardware-bounded, mock remains default)

Made multiple focused attempts to complete the live load + query install. Outcome, honestly:

**PROVEN on real TigerGraph 4.2.3 (the value static analysis cannot give):**
- Schema DDL compiles: 56 vertices + 126 edges + graph created (after fixing finding #1, the
  trailing-semicolon bug).
- All 182 loading jobs compile (after fixing #2 uninitialized FILENAME).
- Data loads: 55/56 vertex types populated — 51 via the GSQL file loader (after #3, the missing
  QUOTE="double"), 4 via live RESTPP using our own RealGraphClient.upsert (coaching_session,
  similarity_match, learning_signal, reasoning_trace). 5th (simulation_scenario, 10 rows)
  pending only a transient RESTPP 408 under concurrent load.
- **RealGraphClient works live against the container** (health + JSON upsert verified) — the
  adapter is not just theoretical.
- 4 distinct real-engine GSQL/loader bugs found and fixed locally (semicolon, FILENAME, QUOTE,
  QUOTE+comma tokenizer) — all to be upstreamed to the foundation package + its validators.

**NOT achievable on this 2-core/8GB codespace (hardware limit, not a code defect):**
- Edge data load: the GSQL file loader wedges/serializes badly under load on 2 cores (got
  6/126 before stalling; restart clears it but it re-wedges). Edge job DEFINITIONS all compile.
- 43-query INSTALL: the C++ query compilation crashes/hangs the GSQL server repeatedly, even
  one query at a time, even with 2.3GB free. This is the documented Section-8 "machine can't
  handle it" case.

**Why this does not block the build:** query SEMANTICS are already independently proven — the
foundation package's validate_query_semantics passes 43/43 (edge directions, source/target
types, attribute refs all resolve), and our MockGraphClient implements all 43 with the same
output contract, verified 43/43 against the package's own query_cases.json. The ONLY unproven
item is real-engine C++ compilation of the queries, which is a hardware constraint here.

**Decision (per CLAUDE.md Section 8):** GRAPH_CLIENT_MODE=mock remains the default working mode.
It is fully verified, instant, and serves all 109,328 rows. local_real is a documented, working
option for a larger box (schema+jobs proven to install; RealGraphClient proven to query/upsert).
Phase 2's core purpose — validate the package compiles/loads on a real engine — is achieved to
the limit this hardware allows; further live validation is deferred to a machine with more cores/RAM.

## Session 2 (cont.) — AI Assistant page + Consolidation sweep

**AI Assistant page (Phase 10 part 5):** rebuilt on real /ai-chat/ask + /agentic-ai/run
(advisor A001, no hardcoded fallback). Chat mode grounds in memory/knowledge/insights with
confidence + reasoning + evidence; agentic mode exposes the multi-agent reasoning path.
Fixed the insights materialize dict bug + wired LLMClient into the chat engine.

**Consolidation sweep:**
- Part 1: deleted 7 backend *-runtime/*-activation routers + 8 hidden frontend runtime routes,
  their components and API modules, and the orphaned old embeddings/memory-explainability
  components. Backend 38->31 routes; frontend 29->18 routes; both build clean.
- Part 2: rewired AgentToolbox (run_predictions/opportunities/recommendations) to the new
  Phase 7/8/9 services. Agentic workflow now surfaces real pipeline artifacts (verified
  recs:3 evidence:5 for A020). Agentic console connects to the same pipeline as /recommendations.

**Consolidation NOT yet done (gated / deferred):**
- Runtime-family backend MODULES (app/features old files, app/memory, app/recommendations old
  runtime files, graph_runtime, knowledge_runtime) remain on disk, now dormant — still imported
  by orchestration/tools.py, ui_integrated services, and app/agents feature/embedding tools.
  Full deletion needs those last callers repointed (feature/embedding agent tools still use old
  FeatureStoreService/EmbeddingSimilarityService).
- /ui-integrated router+services retained: still the data source for 5 unbuilt Phase 11 pages
  (knowledge, whatif, integrated-dashboard, graph-explorer, documents). Delete during Phase 11.
- /orchestration backend router retained (real engine, no frontend); dedup-vs-/agentic-ai
  decision deferred.

Next (Phase 11 breadth): command centers (Exec/DDW/RDW/MDW), Revenue Intelligence, Hierarchy
Explorer, Book of Business, AGP/CRM pages, Graph Explorer, Knowledge, Admin, Data Health (3B);
then delete /ui-integrated + remaining runtime modules once their consumers are rebuilt.

## Session 3 — 2026-07-04 — Part 2B: new agent logic (see VERIFICATION_CHECKPOINT.md §8)

Completed (all with real before/after evidence, mock + claude modes):
- **Revenue Agent** (`app/agents/nodes/revenue_agent.py`): real revenue analysis over
  GraphClient (GQ-004/005/006/008 — LTM, 3m momentum/direction, managed share, top products,
  market-peer gap/percentile). Figures cross-check against the Phase-5 snapshot lineage.
- **Coaching Agent** (`app/agents/nodes/coaching_agent.py`): authors the mockup AI Coaching
  Card (Recommendation/Shoutout/Action Steps/Guideline Basis) via get_llm_client(), grounded
  in the advisor's real snapshot + recs/opps/preds + compliance verdict. Claude-mode runs:
  A001 11.4s / A020 8.7s, advisor-specific figures throughout, visible-error-only fallback.
- **Compliance Agent** (`app/agents/nodes/compliance_agent.py`): replaces the deleted System-B
  "Passed" stub with 4 real rules (prohibited claims / advisory-without-suitability disclosure /
  ≥$50k supervisory review / <0.60 confidence guardrail). All 4 statuses proven reachable;
  always runs after recommendation_agent (supervisor invariant); verdicts on each rec + run.
- Supervisor rewritten: keyword intents for revenue/coaching/compliance, canonical ORDER,
  coaching auto-pulls opportunity->recommendation->compliance ahead of itself. Roster 10->13.
  AgenticResponse gained additive revenue_analysis/compliance_review/coaching_card fields.
- 2A carry-over: InsightGenerationEngine repointed ModelAdapterFactory -> get_llm_client()
  (exec summary + coaching-plan message; visible degradation on LLM error).

Known issues / deferred:
- FLAGGED: InsightDataCollector still reads the OLD FeatureStoreService — advisor feature
  vector returns zeros (Claude summary honestly said "no measurable activity"). Rewire to the
  Phase-5 pipeline in the consolidation sweep (existing deferred item).
- 2C (knowledge/RAG generation step, real semantic embeddings) NOT started, per instruction.

Next: await confirmation, then Part 2C; then Phase 11 breadth + consolidation sweep remainder.

## Session 3 (cont.) — 2026-07-04 — Part 2C-i: real embeddings + RAG generation (see VERIFICATION_CHECKPOINT.md §10)

Completed (backend only, per instruction; frontend 2C-ii not started):
- **EmbeddingClient adapter** (`app/llm/embedding_client.py`): Protocol + `LocalEmbeddingClient`
  (sentence-transformers all-MiniLM-L6-v2, 384-dim, NEW DEFAULT) + `AzureOpenAIEmbeddingClient`;
  `EMBEDDING_CLIENT_MODE=local|azure`. sha256-random mock embeddings fully replaced on the live
  path; `/adapters/status` reports the embedding adapter.
- **Corpus 4→9 documents** (19 chunks): CRM engagement guide, prospecting playbook, client
  review/suitability procedures (incl. the $50k threshold COMP-003 enforces), AGP program
  overview, 2026-Q2 market research. Chroma rebuilt on cosine space; scores now = similarity.
- **Semantic proof**: 5/5 category-targeted queries rank the intended document #1 with real
  cosine margins (e.g. AGP query 0.7264 vs 0.39 next-doc).
- **RagGenerationService** (`app/knowledge/rag_service.py`): retrieve → grounded prompt →
  get_llm_client() → answer + cited sources; 0.30 similarity floor with honest not-found (no
  LLM call, no hallucination). Exposed as AgentToolbox.ask_knowledge + POST /knowledge/ask.
  Retrieval paths consolidated: /ui-integrated/knowledge/search repointed off the mock
  knowledge_runtime onto this one real path.
- **Agent wiring**: RagKnowledgeAgent now does real RAG (generated cited answer, was
  retrieval-only). Coaching Agent's Guideline Basis quotes actual retrieved document text
  (guideline_sources in grounding) — before it cited only playbook_id/compliance status.
  Claude-mode before/after evidence for A001 in §10.

Known issues / deferred: dormant runtime-family module files still on disk (Phase-11 sweep,
unchanged); fastapi now 0.139.0 (lazy router registration — live HTTP verified fine).
Next: await confirmation, then 2C-ii (frontend knowledge/RAG page); then Phase 11 breadth.

## Session 3 (cont.) — 2026-07-04 — Part 2C-ii: Knowledge Hub page + document upload UI (see VERIFICATION_CHECKPOINT.md §11)

Completed (frontend/wiring; closes out 2C). **Verified in a real headless-Chromium browser
(Playwright), not curl** — a live document uploaded end to end:
- **Backend:** `POST /knowledge/upload` (multipart PDF/DOCX/PPTX/TXT) → saves to
  `data/documents/uploads/` (gitignored) → runs the SAME `ingest_document` pipeline 2C-i built
  (real parser → chunk → sentence-transformers embed → Chroma → catalog + graph link) →
  returns document/chunks/assigned-category. Auto-category via existing `_category_for`.
- **Knowledge Hub** (`knowledge-workspace.tsx`): rebuilt OFF fake `/ui-integrated/knowledge/search`
  ONTO real `/knowledge/ask` (RagGenerationService). Ask box + suggestion chips → grounded
  `AiContentCard` answer + cited-sources card (doc name, category badge, color-graded similarity
  meter, excerpt); honest not-found rendered distinctly. Side column: shared upload widget +
  live corpus list. Built from Section-1B tokens/patterns.
- **Shared `document-upload.tsx`** (real `/knowledge/upload`); standalone `/document-ingestion`
  route rewired off fake `/ui-integrated/documents/ingest` onto it.
- **Browser proof:** uploaded a doc NOT in the corpus (`orion_liquidity_directive.txt`) via the
  page → "Indexed ✓ 1 chunk · Practice Guideline"; asked a question about it → grounded answer
  cites it #1 at similarity 0.681. Captured network: `POST /knowledge/upload` + `POST
  /knowledge/ask`, ZERO `/ui-integrated`. `/document-ingestion` re-checked same way: PASS.
- tsc clean; `npm run build` green (18 routes). Verification mutations reverted
  (feature_store.db restored, test uploads removed); `data/documents/uploads/` now gitignored.

Known issues / deferred: unchanged — dormant runtime-family modules + `/ui-integrated` router
removal is the Phase-11 sweep.
Next: **await confirmation before starting Phase 11 breadth pages** (per instruction).

## Session 4 — 2026-07-04 07:14 UTC — Phase 11 PART 1: Mockup-to-build audit (Section 5B item 1)

Viewed every image in `docs/spec/mockups/` directly (8 distinct after md5 dedup — 2 pairs are
byte-identical copies). Sources and what each shows:

| File (md5 short) | What it is |
|---|---|
| `New iperform enterprise design-v2` (291c8986) | Wealth360 grid, **15 pages** numbered 1-15 |
| `Hackathon UI Mock Up` (84e6a30e) | Single flagship "Advisor Revenue Intelligence & AI Coaching Copilot" dashboard (matches current app header). Filter bar = **Hierarchy Level / Advisor / Time Period + Refresh + Last refreshed** |
| `…05_07_17 PM` (567e9265) | iPerform flagship dashboard w/ **AI Intelligence Pipeline (end-to-end)** band, System Trace, "● All Systems Operational" pill, filter = Advisor/Hierarchy/Time Period/Compare To/Filters |
| `…05_07_42 PM` (1e1f6f49) | iPerform grid, **14 pages**; adds **radar** (peer benchmarking), **bar-by-channel**, **region map**, **funnel** (opportunity), **UMAP cluster scatter** |
| `…05_07_57 PM` (436c3192, ×2) | **Definitive current iPerform** grid, 12 pages + full nav. Filter bar = **Persona / Hierarchy BREADCRUMB (West Division › Northeast Region › Boston Market › Alex Morgan) / Time Period / System Status**. Has **Scenario Simulator** page, **gauges** (Advisor Health Score 82, Goal Attainment 68%) |
| `…05_08_51 PM` (4e6b98c4) | Dark-theme "iPerform Insights" exec variant: **Executive Dashboard** (firm rollup), **Client Intelligence 360**, Analytics & Reports, Playbooks. Footer confirms stack: Next.js 14 · TS · Tailwind · ShadCN · **Recharts · React Flow · Framer Motion** |
| `…Jun 16 02_03_42 PM` (a564d056, ×2) | **DDW leadership persona** set, **12 pages**: Executive Overview (FIRM: 218 advisors/$18.7B AUM), Advisor Performance, **AGP Program Dashboard** (74 advisors), Opportunity Explorer, Recommendations Center, **Prediction Insights**, **Peer Benchmarking**, Data Ingestion, **Scenario Simulator**, Memory Timeline, **Admin & Data Quality** |
| `…architecture` (47b1bf91) | Architecture diagram — authoritative **persona list** + **canonical page list** (Layer 1) |

### Personas (from architecture Layer 1) — 4
- **MDW** — Enterprise Leadership (firm-wide) · **DDW** — Division Leadership · **Advisor** —
  Financial Advisor · **AGP** — Advisor Growth Program.
The leadership mockups (DDW set) are the SAME functional pages scoped UP the hierarchy (Executive
Overview = Dashboard@Firm; Advisor Performance = Advisor 360 seen by a leader; AGP Program
Dashboard = AGP@Division). Confirms Section 5B item 3: persona = **data-scoping**, not separate pages.

### GAP TABLE — distinct mockup page → in nav? → real content built? → notes

Build status legend: REAL = wired to real pipeline API; PLACE = pending-rebuild placeholder;
FAKE = component exists but hardcoded/`/ui-integrated`; — = not present.

| # | Mockup page | Nav? | Built | Notes / required Phase-11 action |
|---|---|---|---|---|
| 1 | Dashboard / Exec Dashboard (Advisor + Firm/Div rollup) | Y `/dashboard` | **PLACE** | Flagship page. Build real w/ KPI row, AI insight+coaching cards, pipeline band, revenue trend line, product-mix donut, top opps/recs. **Scope-aware** (firm/div/region/advisor rollup) per Part 4. |
| 2 | Revenue Analytics | Y `/revenue-analytics` | **PLACE** | Tabs Overview/Trend/Mix/Geographic/Product/Cohort. Charts: revenue trend LINE, product-mix DONUT, by-channel BAR, **by-region MAP**, benchmarking. |
| 3 | Advisor 360 / Client 360 | Y `/advisor-360` | REAL | Done (has trend line + account donut). Add Client-Intelligence hierarchy tree if time. |
| 4 | AGP Workspace / Goals & KPIs | Y `/agp` | **FAKE** | Hardcoded JSX (0 API). Rebuild on `app/agp/` — goals table, on/off-track DONUT, milestones, target-vs-actual BAR. |
| 5 | AGP Program Dashboard (leadership) | via `/agp`@scope | — | DDW rollup: 74 advisors, leaderboard, distribution donut. Realize via AGP page + hierarchy scope. |
| 6 | Predictions Center / Prediction Insights | Y `/predictions` | REAL | Done. Leadership variant (growth %, churn risk, prediction trend LINE) via scope. |
| 7 | Opportunities & Recommendations | Y `/recommendations` | REAL | Done (has impact trend line). Mockups also show **Opportunity Explorer** (funnel) + separate Opportunities tab — add funnel + opportunity-by-category donut. |
| 8 | Recommendation Impact / ROI | Y `/recommendation-roi` | **FAKE** | Hardcoded. Rebuild on real feedback/outcome/learning data (accepted/implemented/rejected, business impact, trend LINE) — reuse `/feedback-learning/impact-trend`. |
| 9 | Scenario / What-If Simulator | Y `/what-if` | **FAKE** | Hits `/ui-integrated/what-if/run`. **PART 3** — build real on an advisor's real snapshot + sliders → projected impact. |
| 10 | AI Assistant | Y `/ai-assistant` | REAL | Done. |
| 11 | Knowledge Hub / Search | Y `/knowledge` | REAL | Done (2C-ii). |
| 12 | Knowledge Graph Explorer | Y `/graph-explorer` | **PLACE** | **React Flow** network (advisor↔household↔account↔product↔opp↔rec) + node details. Real graph via GraphClient. |
| 13 | Feature Store / Embeddings / Similarity | Y `/features-embeddings` | REAL | Done (has PCA scatter). Mockups split into Feature Store + Graph Embeddings + Similarity Search — current combined page covers them. |
| 14 | Memory Timeline & Explainability | Y `/memory-explainability` | REAL | Done. Mockup shows a **timeline** treatment + Explainability "why this rec" flow — enhance if time. |
| 15 | Agent Orchestration & Observability | Y `/agents` | **FAKE** | `observability.ts` hardcoded. Rebuild on real `/agentic-ai` roster + agent cards + traces. |
| 16 | Data Ingestion & Sync | Y `/data-ingestion` | **PLACE** | Real upload already exists at hidden `/document-ingestion` + `/knowledge/upload`; wire nav page to it + sync/validation/history (Section 3B Data Health). |
| 17 | Admin / Data Quality / System Status | Y `/admin` | **FAKE** | Hardcoded. Rebuild on `/adapters/status` + `/health` + data-quality counts. |
| 18 | CRM Activities | **N** | — | Meetings/Calls/Notes/Opportunities tables + activity summary. New page on `app/crm/`. |
| 19 | Coaching & Reviews / Advisor Coaching | **N** | — | AI coaching card history + Manager (DDW/MDW) reviews + action items. On coaching agent + `/insights-coaching`. |
| 20 | Peer Benchmarking | **N** (partial in dashboard) | — | **Radar** + rank/percentile + peer-comparison BAR. On GQ-008 peer benchmark. Could be a Revenue-Analytics/dedicated page. |
| 21 | Client Intelligence 360 (client profile) | **N** | — | Dark-variant page: client hierarchy tree, AUM summary line, holdings. Lower priority (Advisor 360 covers advisor side). |

### Phase-11 build order derived from this table (Part 5)
Priority = flagship/most-used first, chart-fidelity rule applied throughout:
1. **Dashboard/Exec** (#1) — scope-aware, flagship. 2. **Revenue Analytics** (#2) — most chart types (map/bar/donut). 3. **AGP Workspace** (#4/#5). 4. **Knowledge Graph Explorer** (#12, React Flow). 5. **Recommendation Impact/ROI** (#8). 6. **Agent Orchestration/Observability** (#15). 7. **Admin/Data Quality** (#17). 8. **Data Ingestion** nav wire (#16). 9. **CRM Activities** (#18, new). 10. **Coaching & Reviews** (#19, new). 11. **Peer Benchmarking** (#20). 12. Opportunity funnel + Client 360 if budget remains.

Preceded by: **PART 2** filter-bar fix (persona + hierarchy breadcrumb + system-status pill,
applied to all pages), **PART 3** What-If Simulator, **PART 4** hierarchy scope-aware data plumbing.

Blockers: none. React Flow not yet a dependency — will add for the graph explorer (part 5 item 4).

## Session 4 (cont.) — PART 2: Filter bar fix (Section 5B item 2) — DONE

- **Removed the duplicate "Advisor / Advisor" dropdown pair** (was persona + scopeType both
  showing "Advisor"). Filter bar is now **Persona · Hierarchy breadcrumb · Period**.
- **Real hierarchy breadcrumb** driven by the graph: new `app/api/routers/hierarchy.py`
  (`/hierarchy/tree` = Firm>Div>Region>Market>Advisor from real edges; `/hierarchy/resolve` =
  advisor ids under a scope via `resolve_scope_advisor_ids`). Breadcrumb renders
  `Northstar Wealth Management › Division 1 › Region 1 › Market 1 › Avery Diaz` with real names;
  each level is a sibling dropdown + a drill-in select. **Verified it actually scopes data**:
  changing the Advisor level Avery Diaz→Reese Patel re-fetched advisor-360 (h1 changed).
- **System-status pill**: `SystemStatusPill` reads `/adapters/status` → "● All Systems
  Operational" (teal) / "Degraded" (amber), replacing the ambiguous "Ready" button + Graph:MOCK.
- Persona type reduced to the 4 architecture personas (Advisor/AGP/DDW/MDW); `defaultScopeByPersona`
  now uses real ids (A001/D01/F001). Shell context gained `scopeLabel`, `hierarchy`, `setScope`.
- advisor-360 wired to shell scope (Advisor scope pins the advisor; rollup scope → first
  descendant). Full scope-consumption across pages is PART 4.
- tsc clean; build green (21 routes). New components: hierarchy-breadcrumb, system-status-pill;
  filter bar rewritten. Screenshot: scratchpad/audit_screens/part2-filterbar.png.

## Session 4 (cont.) — PART 3: What-If Scenario Simulator (Section 5B item 1) — DONE

Route-count correction: the "21 routes" noted in Part 2 was inaccurate — the `page.tsx` set
was byte-for-byte identical to the "18 routes" build (Part 2C-ii), so Part 2 added **no** new
user-facing pages (it only touched the filter-bar/hierarchy/shell components). `npm run build`
now authoritatively reports **19 route entries** (17 dashboard pages + `/` + `/_not-found`);
of those, `/dashboard`, `/data-ingestion`, `/graph-explorer`, `/revenue-analytics` are still
137 B stubs = Part 5 breadth targets.

- **Real backend** (already scaffolded, now verified): `app/whatif/service.py` +
  `app/api/routers/whatif.py` (`POST /whatif/simulate`), wired in `app/api/main.py`. Projects an
  advisor's **real current feature snapshot** (`SnapshotStore.latest_for_entity`, fallback to
  live `compute_advisor_snapshot`) forward under 4 levers (meeting +%, prospecting +%, AUM
  growth +%, added goal reviews) over an adjustable horizon, using **documented, transparent
  elasticities** (not a trained model, not fabricated numbers per CLAUDE.md 5B item 1). Returns
  5 metrics (Total Revenue, Managed Revenue, NNM annualized, AUM, Goal Attainment) each with
  current/projected/change/change_pct **and the computation formula as evidence**, plus baseline
  features + elasticities + a disclosure note.
- **Frontend rebuilt off the fake `/ui-integrated/what-if/run`** onto `/whatif/simulate`:
  `whatif-simulator-client.tsx` now follows the shell scope (Advisor scope pins that advisor;
  rollup scope → first advisor beneath it) with an advisor picker (`/advisor/list`, 60 real
  advisors), real levers, and a Recharts horizontal **% -change-by-metric bar** (positive teal /
  negative red — visualization-fidelity rule) + per-metric current/projected/Δ rows exposing the
  `ƒ formula` and an evidence footer (snapshot id + baseline revenue/AUM).
- **Deleted fabricated dead code**: `lib/api/whatif.ts` old hardcoded `simulateScenario`/
  `explainScenario` (baselines were invented constants), unused `components/whatif/
  impact-comparison.tsx`, `lib/types/whatif.ts`, and the orphaned `runWhatIfScenario` in
  `lib/api/integrated-ui.ts`.
- **Verified end-to-end over HTTP**: `/advisor/list` → 60 advisors w/ real names (A001 = Avery
  Diaz); `/whatif/simulate` A001 (+20% meetings, +10% prospecting, +5% AUM, +2 reviews, 6mo) →
  Revenue 387,293→405,726 (+4.76%), NNM 408,320→420,570 (+3.0%), AUM +2.62%, Goal 27.5→35.5 pts.
  Envelope unwrapping correct. tsc clean; `npm run build` green (19 routes; `/what-if` 6.33 kB).

Next: PART 4 (hierarchy scope-aware data plumbing across pages), then PART 5 (breadth pages per
the Part-1 gap table priority order).

## Session 4 (cont.) — PART 4: Hierarchy scope-aware data plumbing (Section 5B item 3) — DONE

Delivered the scope-rollup engine that makes the hierarchy breadcrumb actually reshape page
data, and proved it end-to-end by building the flagship Executive Dashboard on it (this also
clears Part-5 gap-table priority #1).

- **Backend rollup engine** `app/scope/rollup.py` (`ScopeRollupService`) + `GET /scope/summary
  ?scope_type=&scope_id=` (`app/api/routers/scope.py`, wired in main.py). For any scope it
  resolves advisor ids via the existing `resolve_scope_advisor_ids` primitive, then **sums/means
  each advisor's real latest feature snapshot** (revenue_ltm, aum_total, nnm_3m×4, managed via
  managed_revenue_ratio, goal via kpi_on_track_ratio×100, agp_risk_score banded per the same
  AGP-004 TRACK_BANDS the AGP page uses). Returns totals + **one-level child breakdown** (Firm→
  divisions→regions→markets→advisors, each with its own rollup, powering drill-down) + top
  advisors + evidence (advisor ids resolved, computation formula). No hardcoded firm-wide numbers.
- **Verified aggregation is internally consistent**: Firm F001 revenue 38,365,750 = exact Σ of
  the 3 division revenues; firm advisor_count 60 = Σ child counts. HTTP-verified at Firm (60 adv,
  3 divisions), Division D01 (24 adv, 2 regions), Advisor A001 (1 adv, no children).
- **Flagship Executive Dashboard built** on it (`components/command-center/executive-dashboard.tsx`,
  replaces the `/dashboard` 137 B PendingRebuild stub). Follows shell scope; 8 KPI stat cards,
  **Revenue-by-child bar chart (click a bar → drills the shell scope into that child)**, advisor
  status-mix donut (severity palette), top-advisors table (click a row → scope to that advisor),
  evidence footer. `lib/api/scope.ts` client; new charts `scope-child-bars`, `scope-status-donut`.
- Scope-awareness is now genuinely wired: changing the breadcrumb re-calls `/scope/summary` and
  the whole dashboard re-rolls; drilling a bar/row updates the breadcrumb via `shell.setScope`.
- tsc clean; `npm run build` green — `/dashboard` 5.68 kB (was stub). advisor-360 + what-if
  already follow scope (Parts 2/3); remaining built pages get scope-wired opportunistically during
  Part 5.

Next: PART 5 breadth pages per Part-1 gap table priority — #2 Revenue Analytics (map/bar/donut),
#3 AGP Workspace, #4 Knowledge Graph Explorer, #5 Recommendation ROI, then remaining stubs
(data-ingestion nav wire, graph-explorer) and new pages (CRM Activities, Coaching & Reviews,
Peer Benchmarking).

## Session 4 (cont.) — PART 5 breadth — Revenue Analytics (gap #2) — DONE

- **Backend** `app/revenue/analytics.py` (`RevenueAnalyticsService`) + `GET /revenue/analytics`
  (router wired in main.py). Scope-aware; from REAL `phx_dm_revenue_transaction` records under the
  scope's advisors it computes: monthly revenue trend (24 mo), channel mix (TRAIL/FEE/COMMISSION/
  INTEREST), per-child revenue breakdown (drill-down), and KPIs (total, tx count, avg/advisor,
  top channel). Verified consistent: Σ child revenue == firm total ($74,630,622).
- **Page** `components/revenue/revenue-analytics-workspace.tsx` replaces the `/revenue-analytics`
  stub: 4 KPI cards, 24-month area trend, channel donut, revenue-by-child bar (click drills the
  shell scope), evidence footer — all scope-aware via the breadcrumb, tokens/Recharts per 1B.
- HTTP-verified Firm (24 trend pts, 3 divisions) + Advisor (own revenue, no children). tsc clean;
  build green (/revenue-analytics 9.14 kB, was stub).
- Note: backend dev server must be launched via the harness background runner (plain `&` gets
  reaped when the tool call returns); running on :8010 for verification.

## Session 4 (cont.) — PART 5 breadth — Knowledge Graph Explorer (gap #4) — DONE

- **Backend** `app/graph/neighborhood.py` + `GET /graph-viz/neighborhood?advisor_id=` (router
  wired). Real one-hop subgraph around a focal advisor traversed from the foundation graph: market,
  6 households (advisor_serves_household), CRM opportunities + leads, AGP enrollment + goal, and the
  **AI pipeline artifacts prediction → opportunity → recommendation** (the demo's headline chain,
  now visible as real graph nodes). 19 nodes / 18 edges for A001; every node carries its real
  vertex attributes. Verified for A001 and A005.
- **Frontend** rebuilt `graph-explorer-workspace.tsx` off the fake `/ui-integrated` `/graph/explore`
  onto `/graph-viz/neighborhood`. ReactFlow canvas with a deterministic group-clustered radial
  layout (focal advisor centered), token-based node colors by group (AI artifacts on violet
  AI-accent), animated edges with verbs, group legend, and a **node-detail panel showing the
  clicked node's real attributes** + evidence. Follows shell scope (rollup → first advisor) with an
  advisor picker. Page wired (was PendingRebuild stub); deleted dead `graph-node-card.tsx`.
- tsc clean; build green (/graph-explorer 51.7 kB, real ReactFlow).

## Session 4 (cont.) — PART 5 breadth — Data Ingestion & Sync (gap #8, CLAUDE.md 3B) — DONE

- **Replaced the FAKE `data-ingestion-workspace.tsx`** (hardcoded loads array + fabricated KPIs
  "18"/"1.8K"/"Ready" — a FOUND-005 violation) with a real page on the existing `/ingestion` +
  `/manifest` backend. KPIs (configured entities / graph vertices / edge files / required columns)
  are computed from the real 15-entity `/ingestion/entities` manifest; entity table shows real
  csv/vertex/pk/columns/edges/batch-size per entity; capabilities strip from real `/manifest`.
- **Run Ingestion** button POSTs `/ingestion/run` and renders the **real returned batch_status**
  (total/processed/created/updated/skipped/failed/last-row/progress/checkpoint id + message) —
  honestly showing completed runs (kpi 195, feature_snapshot 168), checkpoint-resume (opportunity:
  "Batch completed; call again to continue"), and validation failures verbatim. No faked "all
  validated".
- `lib/api/ingestion.ts` client added; page wired (was PendingRebuild stub). tsc clean; build
  green (/data-ingestion 5.92 kB).

Known issue (pre-existing, foundation data, not introduced here): several entities' sample CSVs
(advisor, household, transaction) are missing columns their `required_columns` config lists, so
their ingestion run returns status=failed with "Missing required column: …". The ingestion engine
is behaving correctly; the sample CSV/manifest column sets are out of sync for those entities.
Deferred — flag for the foundation-package owner; does not block the page (kpi/feature_snapshot/
opportunity ingest cleanly and demonstrate the real batch/checkpoint flow).

## Session 4 (cont.) — PART 5 breadth — Peer Benchmarking (gap #20, new page) — DONE

- **Backend** `app/peers/benchmarking.py` (`PeerBenchmarkingService`) + `GET /peers/benchmark`
  (router wired). Benchmarks an advisor against the REAL peer group (advisors resolved under the
  scope) via **percentile ranks** of their actual feature snapshots across 6 higher-is-better
  dimensions (Revenue, AUM, Goal Attainment, Client Value, Product Mix, Lead Conversion) — a
  scale-free radar. Nearest peers come from the real `EmbeddingSimilarityService` (deterministic
  similarity v2.0) with scores + reason features. Verified A010=Reese Kim (peer group 60): goal 95th
  pct, AUM 16.7th; nearest Avery Irwin 0.92.
- **Frontend** new page `components/peers/peer-benchmarking-workspace.tsx` + `charts/peer-radar.tsx`
  (Recharts RadarChart, advisor vs 50th-pct peer baseline — CLAUDE.md 5B radar requirement): KPIs
  (peer group / metrics / top strength / biggest gap), radar, metric-detail table (raw values +
  percentile badges), nearest-peers cards (click → scope to that advisor), evidence footer.
  Scope-following advisor picker. Added to nav (Advisor group, new "Radar" lucide icon wired into
  the sidebar iconMap) — first new nav route added this phase.
- tsc clean; build green (/peer-benchmarking 8.89 kB). Nav now 17 items.

## Session 4 (cont.) — PART 5 breadth — CRM Activities (gap #18, new page) — DONE

- **New page** on the existing real `/crm` backend (no new backend needed — leads/referrals/
  opportunities/pipeline/work-summary already real). `components/crm/crm-activities-workspace.tsx`
  + `charts/crm-pipeline-funnel.tsx` (Recharts **Funnel** — the mockup's pipeline-stage viz per
  1B): KPIs (total/weighted pipeline, open opps, overdue), pipeline funnel by stage (real summed
  amounts, canonical stage order), opportunities table, and leads + referrals tables (overdue rows
  highlighted). Scope-following advisor picker.
- `lib/api/crm.ts` client (pipeline/opportunities/leads/referrals). Added to nav (Advisor group,
  new "Contact" icon). Page + route wired.
- tsc clean; build green (/crm-activities 11.4 kB). Nav now 18 items. CRM endpoints HTTP-verified
  (A001: 3-stage pipeline, real leads/referrals with overdue flags).

## Session 4 (cont.) — PART 5 breadth — Coaching & Reviews (gap #19, new page) — DONE

- **Backend** `app/coaching/service.py` (`CoachingReviewService`) + `GET /coaching/advisor/{id}`
  (router wired). Reads real `phx_dm_coaching_session` + `phx_dm_manager_review` vertices via the
  `*_for_advisor` edges; parses `action_items_json`; summarizes session/review counts, avg rating,
  open vs total action items. Verified A001: 3 sessions, 1 review (rating 3.0), 6 action items.
- **Frontend** new page `components/coaching/coaching-reviews-workspace.tsx`: KPIs (sessions/
  reviews/avg-rating/open-actions), coaching-session cards (type, status, summary, action-item
  checklist, next session), manager-review cards (star rating, reviewer, status), evidence.
  Scope-following advisor picker. `lib/api/coaching.ts` client. Added to nav (Advisor group,
  BookOpenCheck icon).
- tsc clean; build green (/coaching-reviews 4.62 kB). Nav now 19 items.
