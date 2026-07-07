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

## Session 4 (cont.) — PART 3/4/5 runtime verification (Playwright, real browser) — DONE

Drove the production build (Next `start` on :3000, backend on :8000) with Playwright across all 8
new/rebuilt pages, capturing console errors + screenshots (scratchpad/s2_*.png):

- **All 8 pages render with 0 console errors and real data populated**: /dashboard ("Avery Diaz
  Overview", KPIs + top-advisor table + evidence), /revenue-analytics (24-mo area trend + channel
  donut with real % + KPIs), /what-if, /graph-explorer (ReactFlow: Avery Diaz centered with the
  prediction→opportunity→recommendation AI artifacts + households/CRM/AGP nodes, labeled edges,
  minimap, legend — 19 nodes/18 edges), /peer-benchmarking, /crm-activities, /coaching-reviews,
  /data-ingestion. Backend endpoints also HTTP-200 verified for a different advisor (A012) to
  confirm generality.
- Screenshots reviewed: dashboard + revenue-analytics + graph-explorer look on-design (token
  colors, dense enterprise type scale, hierarchy breadcrumb, "All Systems Operational" pill).
- First-load `networkidle` timed out once on /dashboard (Next first-request compile); re-verified
  with domcontentloaded → renders clean, 0 errors.
- CORS note: backend allow_origins is :3000/:3001 only — serving the frontend on any other port
  blocks fetches (cosmetic, dev-only). Fine for the standard :3000 dev/demo setup.

Deferred / minor (not blocking, logged for polish):
- Executive Dashboard child-breakdown bar + status donut only render at rollup scopes (Firm/
  Division/Region/Market) — correct by design (an Advisor has no children), but the global default
  persona is Advisor, so the flagship dashboard lands on a single-advisor view. Consider defaulting
  the Executive Dashboard nav entry to Firm scope, or a DDW persona default, for a stronger landing.
- Graph Explorer radial layout is slightly crowded at the bottom cluster (minor node/edge-label
  overlap); pan/zoom/fitView work. Could switch to a tiered dagre layout later.

## Session 4 (cont.) — PART 5 breadth — AGP Workspace REBUILT (gap #3, was FAKE) — DONE

Spot-check found 3 "already built" pages were actually FAKE (hardcoded arrays, no API calls) —
they slipped through the Part-1 "built" classification exactly like data-ingestion did:
`agp-workspace` (hardcoded goals/actions), `recommendation-roi-workspace` (const rows), and
`admin-health-workspace` (const checks). Rebuilding all three real. **This one: AGP Workspace
(gap priority #3).**

- Replaced fake `agp-workspace.tsx` with a real page on the existing `/agp` backend (track-status,
  enrollment, cohort-summary, coaching — all already real). KPIs (risk score / milestone
  attainment / days-to-milestone / program month); **AGP-004 track-status card decomposing the
  risk score into its 3 weighted drivers (attainment_gap/time_pressure/crm_execution_risk) with
  progress bars + the backend's plain-language explanation as evidence**; current-milestone +
  enrollment card; scope-aware **cohort milestone rollup bar chart** (COMPLETED/AT_RISK/UPCOMING/
  ON_TRACK counts from cohort-summary); coaching sessions list. Scope-following advisor picker.
- `lib/api/agp.ts` + `charts/agp-cohort-bars.tsx`. tsc clean; build green (/agp 5.43 kB, was 1.55
  kB fake).

## Session 4 (cont.) — PART 5 breadth — Recommendation ROI + Admin REBUILT (were FAKE) — DONE

Completed the fake-page remediation (all 3 rebuilt; verified via Playwright, 0 console errors):
- **Recommendation ROI (gap #5)** — real on `/feedback-learning/impact-trend` +
  `/recommendations/generate`. Cumulative-reward RL curve (16 rounds), learned per-family weights
  bar (CRM_EXECUTION 1.5 / MANAGED_MIX 0.53 vs baseline 1.0), and a **base × learning_weight =
  priority re-ranking table** — makes the DoD learning-loop centerpiece literally visible.
  Screenshot s3_recommendation-roi.png confirms real data ($1.4M captured impact, 57% accept, cum
  reward 3.8). Charts=2, table rows=2, 0 errors.
- **Admin / Data Quality (gap #7)** — real on `/adapters/status` + `/ingestion/entities`. KPIs
  (vertex/edge rows 24k/85k, row-count mismatches 0, ingestion entities 15); three adapter cards
  (Graph mock / LLM mock deterministic-template / Embedding local MiniLM-384) exposing the actual
  mock/local/real swap-in points; data-load-integrity panel. 0 errors.
- **AGP (gap #3)** re-verified: h2 "Avery Diaz · AGP Goals & Coaching", cohort chart renders, 0
  errors.

Fake-page sweep complete: agp, recommendation-roi, admin, data-ingestion all now real (4 pages
that Part-1 had mis-marked "built"). Note logged: two learning-weight sources differ by design
(persisted state weights 1.14/1.01 applied to recs vs replay-simulation final_weights 1.5/0.53) —
both real, labeled distinctly.

Server-management note: `next start` caches the build at launch; after a rebuild the old server
must be killed by PID (pkill was unreliable here) and restarted, else Playwright tests a stale
build (caused a spurious FAIL round that cleared after a clean restart).

## Session 4 (cont.) — PART 5 breadth — Agent Orchestration & Observability REBUILT (gap #6, was FAKE) — DONE

Found a **5th fake page**: `/agents` (`system-observability-workspace.tsx`) rendered entirely from
hardcoded arrays in `lib/api/observability.ts` (fabricated service health, agent executions,
success rates, cost metrics, error events) — FOUND-005, and it's the agentic-pipeline page (the #1
demo priority).

- Rebuilt real on `/agentic-ai/run` + `/adapters/status`. A **live "Run Workflow"** button executes
  the real supervisor→agents orchestration and renders the ACTUAL trace: reasoning route (5 steps:
  supervisor→context→graph→revenue→explainability→ai_assistant), **6 agent tasks** (agent, real
  instruction, completed status, real per-task durations 1–346 ms), evidence cards (Context Memory/
  TigerGraph/Revenue Agent with scores), final agent + confidence KPIs, and live adapter-mode cards
  (graph mock / llm mock deterministic-template / embedding local MiniLM-384). Verified via
  Playwright: 6 task rows, 5 route steps, 0 console errors (screenshot s4_agents.png).
- Deleted the fake `lib/api/observability.ts`, `lib/types/observability.ts`, and the 4 fake child
  components (agent-metrics-table, error-events-panel, service-health-grid, workflow-trace-list) —
  only this workspace used them. `lib/api/agentic.ts` added.
- tsc clean; build green (/agents 6.49 kB).

**Fake-page sweep now covers 5 pages** (data-ingestion, agp, recommendation-roi, admin, agents) —
all were mis-marked "built" in the Part-1 audit and are now genuinely real. Remaining pages audited
(advisor-360, features-embeddings, memory-explainability, predictions, ai-assistant, knowledge,
document-ingestion) all have real API calls — no further fakes found.

Known backend issue (pre-existing, NOT introduced here, flag for owner): the agentic-ai service
defaults to advisor id `ADV0001`, which does not resolve in the A001-keyed feature/graph store, so
the Revenue-Agent evidence inside a run reports $0 LTM even when advisor_id="A001" is passed. The
orchestration/trace mechanism is fully real; only the revenue figures inside the agent's evidence
are zeroed by the id mismatch. Same root cause as the earlier InsightDataCollector zero-features
note. Needs the agentic service to honor the passed advisor_id / use the A001 id space.

## Session 4 — SESSION-END SUMMARY (2026-07-04 ~21:42 UTC)

Completed (all verified via `npm run build` green + Playwright runtime, 0 console errors, real data):
- **PART 3 — What-If Scenario Simulator**: real projection of an advisor's live feature snapshot
  under 4 levers via documented elasticities; %-change radar-bar + per-metric formulas.
- **PART 4 — Hierarchy scope-aware plumbing**: `app/scope/rollup.py` + `/scope/summary` rollup
  engine (Σ/mean per-advisor snapshots to any scope, drill-down children); flagship **Executive
  Dashboard** built on it (scope-following KPIs, click-to-drill bar, status donut, top-advisor
  table). advisor-360 + what-if + all Part-5 pages also scope-follow the breadcrumb.
- **PART 5 — breadth (7 new/rebuilt priority pages + 5-page fake sweep)**:
  - New/stub→real: Revenue Analytics (trend/donut/by-child bar), Knowledge Graph Explorer
    (ReactFlow real subgraph incl. the AI prediction→opportunity→recommendation chain), Data
    Ingestion (real manifest + live batch/checkpoint runs), Peer Benchmarking (percentile radar +
    similarity peers), CRM Activities (pipeline funnel + leads/referrals/opps), Coaching & Reviews.
  - **Fake pages rebuilt real** (all were mis-marked "built" in Part-1): AGP Workspace (AGP-004
    track-status decomposition + cohort rollup), Recommendation ROI (the learning-loop centerpiece:
    RL reward curve + learned weights + base×weight=priority re-rank table), Admin/Data Quality
    (live adapter modes + graph load report), Agent Orchestration & Observability (live
    /agentic-ai/run trace: route + 6 agent tasks + evidence).
- New nav items added: Peer Benchmarking, CRM Activities, Coaching & Reviews (nav now 19 items).
  Build: 22 routes, **zero 137 B stubs remaining** — every page has real, API-backed content.
- New backend modules/routers: `app/scope`, `app/revenue`, `app/graph/neighborhood`, `app/peers`,
  `app/coaching`, `app/whatif` + routers scope/revenue/graph-viz/peers/coaching/whatif. All
  HTTP-200 verified (incl. a non-default advisor A012) with internally-consistent aggregates.

Known issues / deferred (documented above, none blocking):
- Pre-existing agentic-ai service uses `ADV0001` id space → Revenue-Agent evidence reports $0 for
  A001-keyed advisors (id mismatch; orchestration trace itself is real). Flag for backend owner.
- Several ingestion entities' sample CSVs lack columns their manifest lists (foundation data
  mismatch) → honest "failed" runs on those; kpi/feature_snapshot/opportunity ingest cleanly.
- Executive Dashboard lands at Advisor scope (global default persona=Advisor) so its rollup charts
  only show after switching to a Firm/Division scope — correct-by-design but consider a rollup
  default for the flagship landing.
- Graph Explorer radial layout slightly crowded at the bottom cluster (functional; dagre later).

Next: (1) Client Intelligence 360 (gap #21, last unbuilt mockup page, lower priority); (2) fix the
agentic-ai ADV0001 id mismatch so agent evidence carries real revenue; (3) reconcile ingestion
sample-CSV columns with manifest required_columns; (4) optional dashboard default-scope tweak.

## Session 4 (cont.) — Two flagship-page regressions fixed — DONE

**1. Agentic-ai advisor_id handling (Revenue-Agent $0 bug).** Root cause: `AgenticRequest`
(app/agents/state/agent_state.py) has no `advisor_id` field — every agent keys off
`state.request.scope_id`, which defaulted to `'ADV0001'` (a non-existent advisor in the A001-keyed
store), so all GQ revenue queries returned empty → $0. The frontend was also sending the ignored
`advisor_id` field. Fixes: (a) default `scope_id: 'ADV0001'` → `'A001'`; (b) frontend
`lib/api/agentic.ts` now sends `{question, scope_type:'Advisor', scope_id: advisorId}` (not
advisor_id); (c) added an advisor picker to the Agent Orchestration page (parity with the other
pipeline pages, and required to drive per-advisor runs).
   - **Verified via the actual page (Playwright, 0 console errors)**: run for A001 → Revenue Agent
     "LTM $387,293, momentum +17.7%, peer gap -41.8%"; run for A020 (Riley Adams) → "LTM
     $539,262.90, momentum +2.4%, managed share 15.1%, peer avg $717,599.88, percentile 33".
     Both match the verified snapshots exactly (A001 revenue_ltm 387,293.22 / AUM 10,018,200;
     A020 revenue_ltm 539,262.90 / AUM 25,990,000). Screenshots fix_agents_A001/A020.png.

**2. Executive Dashboard default landing scope → Firm.** `app-shell.tsx` initial scope changed
from Advisor/A001 to **Firm/F001** (label "Northstar Wealth Management", corrected from the live
tree on mount). Persona stays Advisor — scope is a separate breadcrumb-driven data lens, and
setPersona still re-syncs scope only when actively changed, so the Advisor-persona pipeline pages
are unaffected (they resolve Firm → first advisor as before).
   - **Verified (Playwright, 0 errors)**: /dashboard lands as "Northstar Wealth Management
     Overview" — 60 advisors, $38.4M revenue, $2.1B AUM, revenue-by-division bar (2 charts), status
     donut (50/8/0/2), 8-row top-advisor table — meaningful rollup with no manual scope change.
     Screenshot fix_dashboard.png.

Both: tsc clean, build green (22 routes). The agentic ADV0001 known-issue from the prior summary is
now resolved.

## Session 4 (cont.) — Client Intelligence 360 (gap #21, last unbuilt mockup page) — DONE

- **Backend** `app/client360/service.py` + `GET /client/360/{household_id}` and
  `/client/households/{advisor_id}` (router wired). Real household profile from the graph:
  household attrs, serving advisor (advisor_serves_household), accounts (household_owns_account)
  with product holdings (account_holds_product, managed flag), recent transactions
  (transaction_for_household), AI recommendations (recommendation_for_household), and a summary
  (account/holding counts, managed ratio, revenue LTM). Verified H0006: AFFLUENT, 2 accounts,
  8 holdings, 24 txns, 1 accepted rec.
- **Frontend** `components/client360/client360-workspace.tsx` + `lib/api/client360.ts`: household
  picker (scoped to the current advisor's book), KPIs (AUM/accounts/managed ratio/revenue),
  accounts-&-holdings cards with product chips (★ = managed), client-overview grid (segment/risk/
  status/state/advisor), AI-recommendations panel, recent-transactions table, evidence footer.
  Scope-following (advisor → their households). Added to nav (Advisor group, UserCircle icon).
- **Verified (Playwright, 0 console errors)**: /client-360 → "Household 6 Profile" (Avery Diaz),
  Total AUM $297.5K, 2 accounts / 8 holdings, 15 transaction rows, AI rec $36.6K. Screenshot
  fix_client360.png. tsc clean; build green (/client-360 4.88 kB). Nav now 20 items.

## Session 4 (cont.) — Ingestion CSV ↔ manifest required_columns reconciliation — DONE

Root cause: `IngestionService.sample_data_dir` pointed at `tigergraph/sample_data/` — tiny 2-row
STUB CSVs (e.g. advisor columns `advisor_id,name,mdw_id,...`) whose headers no longer matched the
entity-registry `required_columns` (written for the foundation schema `advisor_name`,`total_aum`,
`status`,…). So advisor/household/account/transaction runs failed header validation
("Missing required column: advisor_name; …").

Fix (repoint to the real data, the stronger reconciliation — not aligning to stubs):
- Repointed `sample_data_dir` → `docs/tigergraph_foundation/data/sample/vertices` (the verified
  60-advisor / 10k-transaction foundation dataset the graph store itself loads).
- Reconciled every `required_columns` list in `entity_registry.py` to a verified subset of each
  foundation CSV's actual header; fixed the `transaction` entity's file/vertex
  (`phx_dm_transaction.csv` → `phx_dm_revenue_transaction.csv`,
  `phx_dm_transaction` → `phx_dm_revenue_transaction`).
- **Verified all 15 entities ingest cleanly** (0 "Missing required column"): advisor 60, household
  360, account 720, transaction 10,080, crm_activity 300, agp_goal 24, kpi 5, prediction 120,
  opportunity 120, recommendation 120, feedback 36, memory 136, document 8, feature_snapshot 212,
  embedding 212. account/transaction correctly enter checkpoint/resume ("Batch completed; call
  again to continue").
- **Playwright-verified via the Data Ingestion page** (0 console errors): running `transaction`
  now reads `phx_dm_revenue_transaction.csv` — TOTAL 10,080, FAILED 0, 20% progress, real
  checkpoint id; manifest table shows the corrected CSV/vertex/PK for all 15 entities.
  Screenshot fix_ingestion.png. The prior "ingestion sample-CSV mismatch" known-issue is resolved.


## Session 5 — 2026-07-05 — Consolidation sweep completion + opportunity grounding fix

Continued the consolidation sweep and closed the remaining items with real before/after evidence.

**Sweep items 1-2 (commit a116486) — dormant runtime cluster + /ui-integrated deleted.**
- Item 1: deleted the dormant runtime-family modules (zero live callers — only tethers were
  package `__init__` re-exports, now emptied): `app/features/{similarity,prediction_runtime,
  feature_runtime}.py`, `app/graph/{graph_runtime,tigergraph_production_runtime}.py`,
  `app/knowledge/{knowledge_runtime,chroma_adapter,mock_vector_store}.py`,
  `app/recommendations/{recommendation_runtime,opportunity_engine,learning_engine,learning_store,
  compliance}.py`, and `app/memory/`. Kept live Phase-8 `recommendation_engine`,
  `compliance_validator`, playbook/repo/linker.
- Item 2: deleted both `/ui-integrated` routers + services (all consumers were dead code — the
  `integrated-dashboard` component had no route/nav), unregistered from `main.py`, removed the
  frontend `integrated-ui`/`integrated-expanded` clients + component.
- Items 3 (`/orchestration` dedup) and 4 (`InsightDataCollector` repoint off old
  `FeatureStoreService`) were already resolved in prior sessions.
- Backend 38→36 routes; frontend tsc/build green (25/25 pages).

**Sweep follow-ups (commit 3d6b79c).**
- Gitignored the runtime SQLite DBs (`data/feature_store/*.db`, `data/sqlite/*.db`) and
  `git rm --cached` the two tracked ones — resolves the Session-2 git-hygiene flag. Verified a
  fresh write no longer appears in `git status`.
- Documented the 4 real-engine TigerGraph 4.2.3 GSQL/loader bugs found in Phase 2 in
  `docs/tigergraph_foundation/UPSTREAM_FIXES.md` (trailing `;` after `WITH`, uninitialized
  `DEFINE FILENAME`, missing `QUOTE="double"`, `QUOTE`+comma tokenizer) — each with root cause,
  fix, and a suggested validator check, so the foundation package can fix its own validators.

**Opportunity grounding fix (commit d14289a) — verified, not deferred.**
- Checked whether the legacy `app/services/opportunity_service.py` zero/empty bug reaches
  user-visible output before deferring its repoint. Split by page:
  - **Agentic (`/agentic-ai/run`): NOT affected** — `service_tools.py` only *imported* the legacy
    service (dead import); its `run_opportunities` already used the real
    `OpportunityDetectionService`. Removed the dead import (+ 2 unused request-model imports); no
    behavior change.
  - **Chat (`/ai-chat/ask`): WAS degraded** — `context_assembler` called legacy
    `list_opportunities`, which read an unpopulated repo → **0 opportunity context items**, so a
    chat question about "top opportunities" was grounded in everything except the real
    opportunities. Repointed to `OpportunityDetectionService.detect_for_advisor` (Advisor-scoped).
    Real HTTP before/after: A001 opp-context 0→2 (CRM_EXECUTION 65.4, ADVISOR_GROWTH 49.5),
    A020 0→3 (AGP_MILESTONE 74.8, CRM_EXECUTION 68.1, ADVISOR_GROWTH 56.8) — match Phase-8 exactly.
- Confirmed A020's two 56.8 values are independent: AGP_MILESTONE's 56.8 = the AGP_OFF_TRACK_RISK
  prediction score (`derived_from_prediction=PRED_AGPRISK_A020`, entering as its `intelligence`
  component); ADVISOR_GROWTH's 56.8 = a separate severity composite (`derived_from_prediction=
  None`) from managed-mix features (49.8·.25+35.9·.25+49.2·.20+100·.15+70·.15≈56.8). Coincidence,
  no leakage.

Known issues / deferred:
- Legacy `app/services/opportunity_service.py` now has one remaining consumer
  (`app/services/recommendation_service.py` facade, itself legacy); full deletion gated on
  repointing/removing that facade — separate scoped follow-up.

Next: repoint/remove the `recommendation_service` facade to allow deleting the last legacy
opportunity_service; optional TigerGraph live validation on a larger host.
## Session 6 — 2026-07-05 — Final closure pass (Parts A–E)

**Part A — recommendation_service facade repoint + opportunity_service deletion.** The facade's
`run_recommendations` was dead/broken (called `RecommendationEngine.generate` with the clobbered
signature → TypeError) and was the last consumer of the legacy `OpportunityService`. Repointed it
to delegate to the real Phase-8 `RecommendationService.generate_for_advisor` (uses the real
`OpportunityDetectionService` + persists lineage). Before: TypeError; after A001→2 recs
(74.6/50.0), A020→3 recs (85.3/77.6/57.4). `app/services/opportunity_service.py` then had zero
consumers → deleted. Backend 36 routes. (commit e21dd95)

**Part B — full-system integration test via /ai-chat/ask (6 questions × A001/A020, mock + claude,
+ agentic Q5).** Pipeline connects end-to-end; RAG retrieval is question-adaptive; claude-mode
answers cite real figures that cross-check against verified anchors (387,293 / 539,262 / 25.8 /
56.8 / 0.275 — zero mismatches). Two real gaps found and FIXED:
  1. Recommendations missing from chat grounding (legacy `list_recommendations` → empty repo) →
     repointed `context_assembler` to the real pipeline (A001 Q2 0→2 recs, A020 0→3 recs).
  2. Compliance guardrail unreachable for a prohibited *request* (chat had no compliance; agentic
     `compliance_review` null for Q5) → added a request-level COMP-001 screen in `chat_engine`
     reusing `ComplianceAgent.PROHIBITED_CLAIMS`; Q5 now shows a visible "⛔ Compliance block
     (COMP-001)" in mock AND claude, confidence 0.99, with a COMP-001 reasoning step; normal
     questions unaffected.

In progress: Part C (nav page-by-page reality check), Part D (screenshot pass + fixes),
Part E (final boot/build check).

**Parts C, D, E (completed).**
- Part C: Playwright-loaded all 20 nav routes — all HTTP 200, zero console errors, zero
  placeholder/debug text, all real content. Zero stubs remain. Report in
  docs/qa_screenshots/_qa_report.json (gitignored).
- Part D: screenshotted all 20 pages (docs/qa_screenshots/, gitignored, persistent). In-depth
  visual review of flagship pages vs mockups — high fidelity. Fixed one honesty issue: the
  dashboard Top-Advisors table rendered fabricated "0% / 0 / on-track" for advisors with no AGP
  enrollment (None coerced to 0); ScopeRollupService now emits None → frontend renders "—"/"n/a".
- Part E: backend imports clean (80 real API paths via openapi; zero ui-integrated/remediation/
  runtime/activation routes). Frontend tsc PASS, build green (25/25). Dead-import sweep: cleaned all
  genuinely-dead imports across 12 files, deleted the now-orphaned native_langgraph_collaboration.py
  (agentic pipeline regression-verified 0.85/6-tasks after), kept intentional noqa registration
  imports. Final pyflakes: zero real dead imports.

Session 6 result: consolidation fully closed (opportunity_service + native_langgraph deleted);
full-system chat integration proven (mock + claude) with 2 gaps fixed (rec grounding, COMP-001
request guardrail); 20/20 pages clean; backend/frontend green; zero dead imports. Ready for
client-style testing.

## Session 7 — 2026-07-05 — Section 9 Client Review Round 2 (Phases 0-7)

Model routing: main thread on Opus 4.8; 4 high-stakes design items delegated to the
`fable-architect` (Fable 5) subagent per 9.10/9.11 (9.3 data model, 9.4 MCP adapter, RL
learning-state design in 9.5 Opportunities, 9.6 Revenue Trend Explorer).

### PHASE 0 — shared foundation — DONE
- **9.0 NO PURPLE:** replaced the violet `#7C3AED` AI-accent with indigo-blue `#4F46E5`
  (client's "indigo-blue" example; clearly bluer than the old violet, distinct from severity
  blue `#2563EB`). Updated the `aiAccent` token in `styles/tokens.ts` + `design-tokens.ts`
  (renamed the `violet` palette key → `aiAccent`), and the few hardcoded spots
  (`button.tsx` violet→indigo gradient, `product-mix-chart.tsx` fill, graph-explorer comment).
  Source is purple-free (verified by grep; only remaining hit is a rule-referencing comment).
- **Shared components:** expanded `lib/utils.ts` into the canonical format utility
  (`formatCurrency` with compact/decimals, `formatPercent`, `formatSignedPercent`, `deltaMeta`,
  `pctChange`) and built ONE reusable `components/patterns/delta-indicator.tsx` (icon + up/down
  arrow + signed %/pt, green/red, `positiveIsGood` for lower-is-better metrics). Every Phase 4
  page must use these, not hand-rolled formatting.
- **API base URL (permanent fix):** `lib/api/client.ts` now uses TWO bases — `API_BASE_URL_INTERNAL`
  (loopback) for server-side/SSR/tooling, `NEXT_PUBLIC_API_BASE_URL` (public forwarded URL) for the
  browser, selected by `typeof window`. Documented both in `.env.local.example`; `.env.local`
  (gitignored) carries the live forwarded URL. Port 8000 confirmed Public + CORS regex for
  `*.app.github.dev` (committed last session, e75e809).
- Title-casing: convention set to Title Case for headers; per-page casing handled during each
  Phase 4 rebuild (guardrail: new pages use correct casing from the start).
- tsc PASS.

### PHASE 1 — root-cause fixes — DONE
- **9.1 scope-following** (5 pages): shared `useScopedAdvisor()` hook wired into Predictions,
  Opportunities & Recommendations, AI Assistant, Feature Engineering Lab, Explainability. Verified
  Playwright: /predictions Firm→A001 (25.8/16.7), drill to Division D02→A009 (34.8/26.6) — different
  advisor, different data, 0 errors. (commit cf4e136)
- **9.2 filter bar** (commit 84973f0): Compare-To selector added; Refresh now real (shell
  refreshNonce → scope-following pages refetch without losing scope); Search → /knowledge; Bell
  removed (no notifications backend). Scope persistence across nav verified (drill→A009, navigate
  away+back→still A009). Period dropdown updates state; real period→data filtering deferred to the
  Phase 4 Revenue/Dashboard rebuilds (documented, not a silent gap).
- **Agent Orchestration "Run Workflow"** — DIAGNOSED (per 9.5 hint, checked networking first):
  the button was already wired to POST /agentic-ai/run; the "does nothing" was the same API-base
  issue (browser hitting unresolvable 127.0.0.1:8000). Phase 0's dual-var API base + public port
  8000 + CORS regex fixed it. Verified Playwright: clicking Run Workflow → two 200s from
  /agentic-ai/run, agent trace + confidence % rendered, 0 errors. Not a functional regression.

### PHASE 2 (9.3) — data model + sample-data expansion — DONE (delegated to Fable 5)
NOTE ON MODEL ROUTING: the named `fable-architect` subagent type was NOT resolvable in the running
agent registry (only the .claude/agents/fable-architect.md file exists; available types were
claude/general-purpose/Explore/Plan/etc.). To honor the 9.10/9.11 intent (Fable 5 reasoning for the
4 high-stakes items, main thread stays Opus), I delegated via a general-purpose subagent with an
explicit `model: "fable"` override + the architect guidance embedded. Same mechanism will be used
for the other 3 delegated items (9.4, RL-state design, 9.6).

Fable-5 delivered a BOUNDED, relabel+append expansion (no anchored figures mutated):
- Real-world names: 3 divisions (Eastern/Central/Western), 6 regions, 12 markets, 24 branches (real
  city/state), 360 households ("The Lockhart Family"…), 720 accounts, 64 products (16 sub-cats),
  180 CRM opportunities, 300 varied CRM activities, 72 varied coaching summaries.
- +12 OLDER months → 36 monthly periods (2023-08→2026-07) for trend visuals; older-than-LTM-window
  by construction so trailing-12 LTM + current snapshots are unchanged.
- One new vertex `phx_dm_coaching_task` (90 seed tasks) + 2 edges (+reverse) for 9.5's manager-
  assigns-task feature. Saved-what-if needs no schema change (phx_dm_simulation_scenario exists);
  branch ranking needs none (24 branches + advisor_in_branch).
- Generator: scripts/expand_sample_data_v1_2.py (deterministic, idempotent). Manifest v1.1→1.2.

INDEPENDENT verification by orchestrator (main thread) after restarting the backend on the new data:
- Live API anchors unchanged: A001 revenue_ltm 387,293.22 / aum 10,018,200 / nnm_3m 102,080 / kpi
  0.275; A020 539,262.90 / 25,990,000; firm F001 total revenue 38,365,750.01 (== pre-expansion).
- 36-month trend live for A001 (from 2023-08). Real names live (hierarchy tree "Northstar Wealth
  Management › Eastern Division › Northeast Region"; households "The Lockhart Family").
- scripts/validate_package.py: STATUS PASS — 57 vertices / 128 edges / 185 files / 154,946 rows.
- Deferred (Fable): foundation prose docs still cite old totals (cosmetic); new coaching_task GSQL
  statically-validated only (no live TG compile on this hardware); legacy tigergraph/sample_data/
  untouched (different id-space).

### PHASE 3 (9.4) — TigerGraph 4-tier MCP adapter — DONE (delegated to Fable 5)
Fable-5 built ONE `TieredGraphClient` (app/graph/tiered_client.py) behind the unchanged GraphClient
interface: Tier 1 MCP (tigergraph-mcp stdio) → Tier 2 pyTigerGraph → Tier 3 RESTPP (RealGraphClient)
→ Tier 4 Mock. Automatic fallback with per-tier cooldown; per-request tier logging
(app/graph/tier_log.py) surfaced to the Admin page via GET /adapters/status → new `graph_tiers`
{mode, chain, usage{total_served, served_by_tier, recent_requests}}. Each query result carries
served_by_tier. Mode routing: mock → raw MockGraphClient (unchanged, preserves isinstance + .store
callers); auto|tiered|mcp → full chain; local_real|real → pyTG→RESTPP→mock. SDK imports lazy inside
tier classes (missing package never breaks the mock path).

Beyond the guardrail, Fable started the existing Docker TG container (bounded, one attempt) and
LIVE-VERIFIED all 4 tiers: Tier 1 MCP read round-trip healthy, Tier 2 pyTG echo "Hello GSQL", Tier 3
RESTPP healthy, full-chain cascade 1→2→3→4 with mock serving GQ (queries never INSTALLed on-engine —
the documented Phase-2 C++ hardware limit, unchanged) and the full fallback trail logged. GPE wedged
under load on 2 cores (SYS-0001/503, correctly propagated) — stopped per guardrail, container
returned to exited state. Also fixed a live bug in tigergraph_mcp_stdio_client.py (dict-valued query
params crashed `value in {None, ""}`).

New env vars (for 9.9): TG_HOST, TG_GRAPHNAME, TG_USERNAME/TG_PASSWORD, TG_API_TOKEN, TG_RESTPP_PORT,
TG_GS_PORT, GRAPH_TIER_COOLDOWN_SECONDS, GRAPH_TIER_PROBE_TIMEOUT_SECONDS, TIGERGRAPH_MCP_COMMAND/ARGS;
GRAPH_CLIENT_MODE gains auto|tiered|mcp. All defaults mock-friendly.

Orchestrator independent verify (backend restarted, mock mode): A001 revenue_ltm 387,293.22 unchanged;
/adapters/status → graph_tiers.mode=mock, chain=[tier4], per-request logging works (total_served
counting). Deferred: frontend Admin UI to render graph_tiers (Phase 4 Admin rebuild); a parallel
legacy graph-access stack still duplicates this (consolidation candidate, out of 9.4 scope).

### PHASE 4 — page rebuilds (commit per page)
**Page 1/16 — Executive Dashboard (9.5) — DONE.** Shared KpiStatCard now renders a colored
icon-in-soft-circle + the Phase-0 DeltaIndicator; every dashboard KPI got an icon; Revenue (LTM)
shows a real prior-year delta (-7.4%, from a new backend `comparison` block = trailing-12 vs prior-12
of the 36-month trend). Added: AGP Program Status card (on/attention/urgent/critical counts +
View Details→/agp), Top Advisors AND "Needs Attention" (bottom) tables each with a stated reason
(new backend bottom_advisors + reason). Refresh button now re-fetches the dashboard (refreshNonce).
Bug fixed: TRACK_BANDS had gaps (39→40, 69→70, 84→85) so fractional risk like 39.9 fell through to
"critical" — `_band` in rollup.py AND agp/service.py rewritten to gap-free thresholds (verified 39.9→
on_track, anchors 25.8→on_track / 56.8→attention unchanged). Verified Playwright: dashboard renders
icons + delta + AGP card + both tables, 0 errors. tsc PASS.

**9.2 Period wiring COMPLETED (was deferred from Phase 1).** RevenueAnalyticsService.analytics now
takes a `period` (MTD/QTD/YTD/LTM/ALL), filtering transactions by a window anchored to the latest
data month; router + revenue page pass shell.period and re-fetch on change. Live-verified the Period
dropdown now changes data: Firm ALL 15,116 tx/$109M → YTD 2,940/$22.2M → MTD 420/$3.4M. Guardrail:
analytics default (no period) = ALL = full 36 months, so the dashboard prior-year `comparison`
(-7.4%) is unaffected. tsc PASS.

## Session 8 — 2026-07-05 (resumed after overnight codespace stop)
Servers restarted cleanly (backend :8000 mock + `--reload`, frontend :3000; port 8000 re-set Public
after the restart reset it to private — visibility does NOT survive a codespace stop). Pushed the 70
local commits to origin/main first (origin now 72 commits, tip 81c7168). Added reusable QA scripts
`frontend/scripts/shot.mjs` (screenshot + console-error capture) and `verify-revenue-scope.mjs`
(interactive scope-following check) — carry these forward for the remaining Phase 4 pages.

**Page 2/16 — Revenue Analytics FULL rebuild (9.5/9.12) — DONE.**
- **"Revenue by scope" diagnosis:** backend `by_child` drill-down was already correct at every
  level (curl-verified FIRM→3 div, DIVISION→2 region, REGION→2 market, MARKET→6 advisor, ADVISOR→0).
  The actual visible defect was the **Revenue-by-Channel donut rendering blank** (ResponsiveContainer
  measure race inside a fixed 180×180 flex child — same pattern as `account-mix-donut`). Fixed by
  building the new donut at a FIXED PieChart pixel size (no ResponsiveContainer) with animation off.
- **Backend (`app/revenue/analytics.py`)** now returns three distinct real breakdown dimensions plus
  a prior-year comparison, all Σ revenue_amount over the scope's resolved advisors:
  - `by_business_line` — transaction_for_product → product_in_subcategory → subcategory_in_category
    (8 categories: Managed Accounts / Brokerage / Fixed Income / Equities / Mutual Funds /
    Alternatives / Cash & Lending / Insurance). product→category resolved once (64 products).
  - `by_channel` — transaction_type (FEE/COMMISSION/TRAIL/INTEREST), now rendered as a **bar**.
  - `by_geography` — advisor_in_branch → branch.state (10 states firm-wide: CA/TX/MI/IL/FL/GA/MA/NY/
    AZ/CO), scope-aware (Central Division → 3 states TX/MI/IL).
  - `comparison` — same-period-prior-year (months shifted −12). **Coverage-gated**: change_pct is
    suppressed (None) when the prior window isn't fully in the data, so ALL (36mo, partial prior)
    shows no delta while YTD (−0.8%) and LTM (−7.4%, matches the dashboard) do. Single traversal per
    advisor keeps advisor identity for the geo attribution.
  - Anchors unchanged: FIRM ALL total $109,256,399 / 15,116 tx (== pre-rebuild).
- **Frontend**: new `components/charts/revenue-state-map.tsx` (US tile-grid cartogram, zero new deps,
  sequential blue fill by revenue, ranked list, theme-safe) and `components/charts/revenue-donut.tsx`
  (fixed-size donut with the total centered inside the ring per 9.5). Workspace rebuilt: KPI cards
  now use icons + the shared DeltaIndicator (Total Revenue shows vs-prior-yr, green/red), trend area
  with prior-year annotation, Business Line donut, Channel bar, geographic map, scope drill-down bar,
  updated evidence footer. Uses shared `formatCurrency`. **Fixed refreshNonce dep** so the shell
  Refresh button re-fetches this page.
- **Verified**: tsc PASS; Playwright 0 console errors at FIRM ($22.2M/10 states) AND drilled Central
  Division ($7.4M/3 states, childHeading→Region, evidence "20 advisors under DIVISION D02") →
  scope-following PASS. Screenshots: docs/qa_screenshots/revenue-after-firm.png, revenue-after-division.png.

**Page 3/16 — Advisor 360 / Client 360 (9.5) — DONE.**
- Reused the existing Phase-5..9 insight engine (`/insights-coaching/generate`) — no new AI backend.
  New `app/ai/insights/structured_view.py` reshapes its payload into the exact client sections:
  AI Insight Summary = Key Drivers / Watch Outs / What to Monitor; AI Coaching Card = Recommendation
  / Shoutout / Action Steps / Guideline Basis. Deterministic, grounded only in real card evidence.
  New endpoint `GET /advisor/360/{id}/ai` (read-only: write_to_memory/tigergraph=False).
- New `app/embeddings/similar_entities.py`: extends advisor similarity to **households & accounts**
  via real cosine NN over persisted `phx_dm_embedding.vector_preview` vectors (60 HOUSEHOLD + 60
  ACCOUNT embeddings). advisor_360 response now carries `crm_opportunities` (CRM-003, with
  stage/status for outcome coding), `segment_mix` (household segment split), and `similar`
  {households, accounts} for the advisor's largest-AUM embedded entity.
- Frontend: two reusable pattern components `ai-insight-summary.tsx` + `ai-coaching-card.tsx`
  (wrap the shared AiContentCard "✦ AI Generated" chip) — will be reused on Dashboard/Client 360.
  Workspace rebuilt: structured AI cards (load async), AGP card adapts (enrolled → risk score;
  NOT enrolled → explanatory copy, no dead card), CRM Execution outcome cards color-coded
  (won=green/lost=red/negotiate=amber via `outcomeTone`), Households-by-Segment bars, Similar
  Households/Accounts with cosine % bars, households table gained AUM + a real "View AI lineage"
  link to /memory-explainability (replaced the vague "AI artifacts" counter block). refreshNonce dep.
- **Verified**: tsc PASS; Playwright 0 console errors on A001 (enrolled, AGP 19.7/on_track, WON/LOST/
  NEGOTIATE CRM cards, similar Lockhart→Eastman 100%/Everhart 96%/Kirkland 95%) AND A025 (Reese
  Patel, non-enrolled → AGP "NOT ENROLLED" adaptive copy, entirely different data $595.6K, similar-
  entities honestly show "No embedding available") → scope-following + AGP adaptation both PASS.
  Screenshots: advisor360-after-a001.png, advisor360-after-a025.png.

**Page 4/16 — AGP Goals & Coaching (9.5/9.12) — DONE.**
- Backend: new `AgpService.kpi_scorecard(advisor_id)` + `GET /agp/kpi-scorecard/{id}` — per-KPI
  Target vs Current, attainment %, on/off-track status and an 8-point milestone history, traversed
  advisor→enrollment→milestone_progress→kpi_measurement→kpi over real `phx_dm_agp_kpi_measurement`
  rows (960 measurements, 5 KPIs). Verified per-advisor variation (A001 3 OFF_TRACK vs A009 mostly
  ON_TRACK). Coaching already varies per advisor (8 distinct summaries across 72 sessions from the
  Phase-2 expansion) — confirmed, no change needed; now render action_items_json too.
- Frontend: new `kpi-gauge.tsx` (radial attainment meter, on/off-track color) + `kpi-target-actual.tsx`
  (Target-vs-Actual grouped bars WITH legend). Added a legend to `agp-cohort-bars.tsx`. Workspace
  rebuilt: KPI Attainment Meters row (5 gauges), Goals & KPIs table (Target/Current/Progress
  bar/Status color-coded) with row-select drill-in → Target-vs-Actual chart, Program Milestones
  strip (Completed/In-Progress/Not-Started from milestone_progress status), Cohort rollup w/ legend,
  AI KPI Insights (reuses `AiInsightSummary` fed by /advisor/360/{id}/ai — grounded), coaching
  sessions with action-item checklists. Non-enrolled advisors get a clean "not enrolled" state.
  refreshNonce dep. KPI cards gained icons.
- Verified: tsc PASS; Playwright 0 console errors on A001 (5 gauges, drill-in chart, milestone
  statuses, AI insights, varied coaching). Screenshot: agp-after-a001.png.

**Page 5/16 — Client Intelligence 360 (9.5) — DONE.**
- Backend (`app/client360/service.py`): each household recommendation now carries a `lineage`
  block explaining HOW it was reached — traversed from real edges:
  recommendation_addresses_opportunity, recommendation_based_on_prediction,
  recommendation_uses_feature_snapshot, recommendation_uses_playbook (sources) +
  reasoning_for_recommendation → reasoning_trace (reasoning_steps_json + evidence_json, with
  id/type plumbing filtered out). Added `similar` {households, accounts} via `similar_entities`
  (cosine NN over embeddings) for the household + its top account (30 households have recs).
- Frontend: AI Recommendations card rebuilt to the structured standard — title + action + impact/
  confidence/priority/status, then a "How this was reached" panel (numbered reasoning steps +
  evidence chips + Opportunity/Prediction/Feature-Snapshot source pills) with the ✦ AI Generated
  chip. New Similar Households + Similar Accounts/Portfolios cards (cosine % bars).
- Verified: tsc PASS; Playwright 0 console errors — The Lockhart Family renders full profile,
  rec "Review relationship growth opportunity" shows 6 reasoning steps + OPP_HH_H0006 +
  FS_HH_H0006_202607 sources, similar households Eastman 100%/Everhart 96%/Kirkland 95%.
  NOTE: uvicorn --reload mid-restart can transiently blank the page (no per-page retry-on-error,
  a pre-existing app pattern); recovers on reload/Refresh. Screenshot: client360-after.png.

**Page 6/16 — Coaching & Reviews (9.5/9.12) — DONE (includes a genuine new feature).**
- Coaching sessions already vary per advisor (Phase-2 data, 8 distinct summaries) — verified; now
  resolve coach_user_id/reviewer_user_id → real manager identity (display_name + role_code via
  phx_dm_persona_user) on every session and review.
- **NEW manager-assigns-task feature** (real CRUD, not a display fix): extended
  `app/coaching/service.py` with a selectable TASK_CATALOG (6 templates) + `tasks()` /
  `create_task()` / `update_task_status()` persisted through the GraphClient adapter (upsert_vertex
  + upsert_edge into phx_dm_coaching_task + _for_advisor/_assigned_by edges; the mock upsert writes
  the same indexes the read path traverses, so tasks are immediately retrievable). Router:
  GET /coaching/task-catalog, GET /coaching/tasks/{id}, POST /coaching/tasks,
  PATCH /coaching/tasks/{id}/status. **Real AI read path**: `open_tasks_for_context()` wired into
  `app/ai/chat/context_assembler.py` (new ChatContextSource.COACHING_TASKS) so a manager's assigned
  task actually steers the AI Assistant — VERIFIED: assigned "Focus on ESG portfolio migration" →
  it appears in /ai-chat/ask context items for A001. CRUD roundtrip verified (create→retrieve→
  complete, all persisted; note: mock upserts are in-memory, reset on backend restart).
- Frontend: apiClient gained `patch()`. Workspace adds a "Manager · Assign Coaching Task" card
  (template dropdown + instruction preview + Assign button) and a live task list with color-coded
  priority + click-to-cycle status (OPEN→IN_PROGRESS→COMPLETED). Sessions/reviews now show manager
  identity (name + role). KPI "Open Coaching Tasks".
- Verified: tsc PASS; Playwright 0 console errors; task assignment + status cycling functional.
  Screenshot: coaching-after.png.

**Page 7/16 — CRM Activities (9.5/9.12) — DONE.**
- **Funnel diagnosis + fix**: the Recharts `<Funnel>` misrendered because it needs monotonically-
  descending values but per-advisor data mixes terminal WON/LOST bands with open stages at
  non-monotonic amounts (A001: NEGOTIATE 405k, WON 105k, LOST 255k). Replaced with a deterministic
  CSS stage funnel (`crm-stage-funnel.tsx`): canonical OPEN stages (Prospect→Qualify→Propose→
  Negotiate) always render in order (zeros included) as centered trapezoid bands, width ∝ open
  opportunity count; Won/Lost shown as separate outcome chips. Reads as a funnel regardless of sparse
  per-advisor data.
- Backend: new `CrmService.activities()` + `GET /crm/activities/{id}` — reads the 300
  phx_dm_crm_activity records (5/advisor: MEETING/CALL/EMAIL/REVIEW/FOLLOW_UP) via
  activity_for_advisor, resolves the household via activity_for_household ("With"), returns by_type
  counts, this_week window, recent_meetings and upcoming. Varies per advisor (A001 Whitfield vs A009
  Donnelly).
- Frontend: Activities This Week (5 icon-count cards), Recent Meetings table with the EXACT columns
  Date/Subject/With/Type/Outcome(status+sentiment color)/Next Step, Recent Notes (per-activity
  notes_summary, varies per advisor). refreshNonce dep.
- Verified: tsc PASS; Playwright 0 console errors. Screenshot: crm-after.png.
- DEFERRED (honest): a literal calendar-grid view was not built — the `upcoming` agenda data is
  returned by the API and Recent Meetings/This Week cover the intent; a calendar grid can be added
  in a later polish pass. Per-advisor CRM volume is thin (5 activities, 3 opps each) — that's the
  Phase-2 seed reality, not a bug; richer volume would need another data-expansion pass.

**Page 8/16 — What-If Simulator (9.5) — DONE.**
- Backend: `RecommendationService.save_scenario_as_recommendation()` persists a What-If result
  through the SAME real pipeline generate_for_advisor uses — upsert recommendation vertex
  (type SCENARIO_ACTION, category, high_priority→CRITICAL/priority 92) + recommendation_for_advisor
  + uses_feature_snapshot edges + a reasoning_trace grounded in the scenario levers/projection; also
  persists a phx_dm_simulation_scenario vertex (+scenario_for_advisor) for provenance. New
  `list_for_advisor()` + `GET /recommendations/advisor/{id}` reads persisted recs; new
  `POST /whatif/save-recommendation`. VERIFIED roundtrip: saved What-If rec appears alongside the 3
  engine-generated recs in /recommendations/advisor/A001 (SCENARIO_ACTION, CRITICAL, priority 92).
- Frontend: apiClient already had post; added save panel to the simulator (category dropdown,
  High-priority checkbox, Save button) with a live confirmation showing the persisted
  recommendation_id + scenario_id + projected impact.
- Verified: tsc PASS; Playwright drove Run→Save, 0 console errors, confirmation rendered.
  Screenshot: whatif-after.png.
- NOTE: mock upserts are in-memory (per running process) and reset on backend --reload/restart —
  same documented behavior as the coaching-task feature; fine for the demo session.

**Page 9/16 — Predictions & Forecasting (9.5) — DONE.**
- Scope-following already in place (`useScopedAdvisor`, Phase 1) — verified it follows the breadcrumb.
- Backend: added a `methodology` block to both prediction results (`PredictionService._methodology`):
  model name/family/version, the 6-step derivation pipeline (feature snapshot → select drivers →
  weight each → sum+clamp → band+confidence → persist trace), features_used, and the score formula.
  Honest framing — these are transparent additive scorecards (real per-feature weights), with the
  scikit-learn RandomForest engine noted as the trained alternative. Predictions already carried
  per-feature `contributions` (feature/value/points/why) + explanation + reasoning trace.
- Frontend: each prediction card gained a "How this was derived" panel (model chip + pipeline steps
  + ƒ formula + trained alternative) beneath the contribution bars + evidence pills.
- Verified: tsc PASS; Playwright 0 console errors (Revenue Decline 16.7, AGP Off-Track 25.8, both
  with methodology panels). Screenshot: predictions-after.png.

**Page 10/16 — Opportunities & Recommendations (9.5) — DONE (flagship; RL showcase delegated to Fable).**
- Scope-following already in place (useScopedAdvisor). Main-thread additions: outcome summary cards
  (Accepted/Completed/In-Progress/Rejected with counts + % + green/amber/red, from impact_trend
  totals); color-coded action-family category tags with icons (MANAGED_MIX/RETENTION/CRM_EXECUTION);
  color-coded feedback buttons (ACCEPT/COMPLETE green, MODIFY amber, IGNORE gray, REJECT red);
  KPI icons. Impact-over-time chart already existed (kept).
- **RL learning-state showcase — DELEGATED TO FABLE-5** (general-purpose subagent, model:"fable",
  per 9.10/9.11). Fable enhanced `impact_trend()` (per-round `weights` snapshot per family +
  top-level `families` + `baseline_vs_learned` with positive/negative event counts, all pure
  computation, existing keys preserved) and built a self-contained `LearningStateShowcase`
  component (default export, zero props, fetches /feedback-learning/impact-trend). Three beats:
  (1) the 5 real ACTION_SIGNALS as color-coded pills; (2) CENTERPIECE — Recharts weight-trajectory
  line per family across the 16 replayed feedback rounds with a dashed neutral-1.00 reference line
  + legend (CRM_EXECUTION 1.14→1.50, MANAGED_MIX 1.01→0.53 — client can SEE lines diverge);
  (3) baseline→learned per family with arrows, signal counts, and a data-derived plain-language
  takeaway ("Advisors kept completing CRM Execution actions, so the system ranks them ~32% higher";
  "kept rejecting Managed Mix … ~48% lower"). No purple; skeleton/empty states; tsc clean.
  Main thread integrated it (replaced the old flat weights grid).
- Verified: tsc PASS; Playwright 0 console errors; whole page renders (summary cards, category tags,
  colored buttons, RL showcase with weight-divergence chart + takeaways). Screenshot:
  recommendations-after.png.

**Page 11/16 — Recommendation Impact / ROI (9.5) — DONE.**
- Root cause of the static top cards: `fetchImpactTrend()` never passed an advisor, so it always got
  the endpoint's default firm-wide cohort (`?advisor_ids=A001,A002,...`) regardless of selection.
  Fix: `fetchImpactTrend(advisorIds?)` now passes `?advisor_ids=`, and the workspace calls it with
  the selected `advisorId` (+ refreshNonce dep). Captured Impact / Accept Rate / Feedback Events /
  Cumulative Reward / reward curve / weights / re-ranked table all now scope to the advisor. Header
  + subtitle name the advisor; KPI icons added.
- Verified: per-advisor API differs (A001 2 events/$129,600/reward 0.1 vs A020 3/$321,712/1.1);
  tsc PASS; Playwright 0 console errors, page shows "Avery Diaz · Outcome & Learning Loop" with
  scoped values. Screenshot: roi-after.png.

**Page 12/16 — AI Assistant + Knowledge Hub (9.5) — DONE.**
- New reusable `components/patterns/formatted-answer.tsx` — lightweight structural renderer (no
  markdown dep): "Label:" → indigo section header, `-/•/*` → bullets, `1.` → numbered list, blank
  line → paragraph, `**bold**` inline; strips the mock-LLM `[mock-llm <hash>]` / "Deterministic
  draft based on:" noise so mock output reads cleanly (real Azure/Claude output has no such tag).
- AI Assistant (scope-following via useScopedAdvisor, verified): answers now render via
  FormattedAnswer (sectioned: Insight Summary / Top Recommendation / Top Opportunity / Next Action);
  agentic evidence raw-JSON `<pre>` replaced with a clean labelled list; single-line `<input>`
  replaced with a larger multi-line `<textarea>` (rows=3, resize-y, Enter=send / Shift+Enter=newline).
- Knowledge Hub: answer rendered via FormattedAnswer under an "Answer" section label; "Cited Chunks
  (N) · with similarity scores" header; each chunk keeps its color-coded similarity meter (0.639
  teal → 0.339 amber) + category badge — distinct color-coded sections per the spec.
- Verified: tsc PASS; Playwright drove a suggestion on each page, 0 console errors, structured
  output rendered. Screenshots: assistant-after.png, knowledge-after.png.

**Page 13/16 — Feature Engineering Lab (9.5) — DONE.**
- Scope-following (useScopedAdvisor) verified. Feature computation cross-checked: A001 anchors match
  every prior verification (revenue_ltm 387,293.22 / aum_total 10,018,200 / nnm_3m 102,080 /
  kpi_on_track 0.275); 33 features across 8 groups (Revenue/Book/Peer/CRM/AGP/Feedback/Graph/Risk);
  similar advisors A004 0.858 … A011 0.744.
- **Visual lineage** (was a raw JSON `<pre>`): new `feature-lineage-diagram.tsx` renders the real
  source→feature flow as connected stage nodes with arrows — Graph Evidence (the feature's real
  evidence facts) → Source Query (GQ-### / computation) → Feature (name + group badge + value) →
  Consumed By (Feature Snapshot → Predictions → Opportunities & Recommendations). Feature table rows
  are click-to-select and drive the diagram; replaced the cramped side panel with a full-width flow
  card + a Feature Groups summary. Verified live: revenue_ltm → GQ-004 get_revenue_summary_by_scope,
  evidence {window, transaction_count 91}, value 387,293.22.
- Verified: tsc PASS; Playwright clicked a feature, 0 console errors, diagram rendered.
  Screenshot: featurelab-after.png.

**Page 14/16 — Explainability Explorer (9.5) — DONE. ← LAST PHASE-4 PAGE REBUILD; PHASE 4 COMPLETE.**
- Scope-following (useScopedAdvisor) verified. Lineage chain made client-legible: each stage
  (Feature Snapshot → Prediction → Opportunity → Recommendation → Feedback → Outcome → Learning)
  now shows a human-readable one-line summary derived from the real vertex attributes (e.g.
  Opportunity "PIPELINE_ACCELERATION · sev ATTENTION", Recommendation title) instead of raw ids.
  Evidence panel: raw-JSON `<pre>` replaced with a clean key/value list (opportunity/prediction/
  playbook ids, base/adjusted priority, learning weight).
- **Real Memory Timeline** (was absent): fetches /memory/retrieve (scope_type "Advisor") and renders
  a vertical temporal timeline of the advisor's memories — type badge (Conversation/Semantic/
  Coaching, color-coded), timestamp, confidence, source, and Q/A summary. Live content present
  (conversation memories written by the AI Assistant, incl. compliance-block memories).
- Verified: tsc PASS; Playwright 0 console errors; chain + evidence + memory timeline all render.
  Screenshot: explainability-after.png.

============================================================================================
## PHASE 4 COMPLETE (all 14 page rebuilds done, pages 1-14). Every page: real backend logic,
## tsc clean, Playwright 0 console errors, screenshot in docs/qa_screenshots/, committed + pushed.
============================================================================================

## PHASE 5 — Revenue Trend Explorer (9.6) — DONE (Fable-5 designed).
- Fable built `app/revenue/trend_explorer.py` (`RevenueTrendExplorerService`, analytics.py
  untouched) + `GET /revenue/trend` (params: dimension [division|region|market|branch|advisor|
  business_line], granularity [monthly|quarterly], start/end YYYY-MM, scope_type/scope_id). Per
  period: total_revenue, prior_revenue, change_pct (vs immediately preceding bucket, computed from
  full data so the first in-range period still has a real prior), slice breakdown (top-5 + Other),
  top_slice, and an AI `driver_summary` (get_llm_client, grounded ONLY in that period's computed
  figures). Real: per-advisor→dimension mapping via hierarchy edges; business_line via
  transaction_for_product→subcategory→category; Σ revenue_amount over real transactions.
- Fable built self-contained `revenue-trend-explorer.tsx` (default export, zero props, self-fetches,
  reads ShellContext so it follows the breadcrumb): Slice-By select (6 dims), Monthly/Quarterly
  toggle, From/To month range; stacked Recharts bars in fixed slice order (Other = muted slate),
  legend, currency axis; click-a-bar → Period Drivers card (AiContentCard "✦ AI Generated" chip)
  with total, DeltaIndicator vs prior, driver summary, per-slice figures, evidence. No purple;
  dataviz palette validated. Main thread integrated `<RevenueTrendExplorer />` into the Revenue
  Analytics page.
- Verified: tsc PASS; endpoint curl-verified (division/quarterly 13 buckets, business_line 8→top5+
  Other, real deltas); Playwright 0 console errors, stacked bars + AI driver card render (tall-
  viewport capture — below-fold Recharts under-measure in headless fullPage, a capture artifact
  only). Screenshot: revenue-trend-explorer.png.

## PHASE 6 — DONE.
- **9.8 RAG corpus**: new `scripts/generate_rag_corpus_docs.py` writes 6 realistic practice-mgmt
  docs across formats (2 PDF via reportlab, 2 DOCX via python-docx, 2 PPTX via python-pptx) into
  data/documents/sample_knowledge (Reg BI Suitability Manual, Market Outlook, Managed-Account SOP,
  AGP Milestone Recovery, AGP Onboarding deck, Referral/COI workshop). Fixed
  `ingest_sample_knowledge` to glob ALL supported suffixes (.txt/.md/.pdf/.docx/.pptx), not just
  .txt — so the real multi-format parsers are exercised. Verified: parsers read all 3 formats;
  ingest = 15 docs incl the 6 new-format ones; retrieval — the new `reg_bi_suitability_manual.pdf`
  is the TOP cited source (sim 0.663) for "supervisory principal review threshold". (Non-issue
  noted: `/knowledge/ask` body field is `query` not `question`; re-ingesting duplicates chunks in
  the in-memory store — resets on reload.)
- **9.9 .env.example**: complete — every var in use documented (already committed).

## PHASE 7 — closing verification — DONE.
- **No-purple audit**: grep for violet/purple hex + tailwind purple classes across frontend →
  clean (only the aiAccent indigo remains, which is the approved 9.0 replacement).
- **Backend boot**: `from app.api.main import app` imports cleanly; OpenAPI reports **90 documented
  paths**; all 7 new Section-9 endpoints registered (/revenue/trend, /coaching/tasks,
  /advisor/360/{id}/ai, /agp/kpi-scorecard/{id}, /whatif/save-recommendation,
  /recommendations/advisor/{id}, /crm/activities/{id}).
- **Frontend**: `npx tsc --noEmit` exit 0 (whole app). All 11 rebuilt page routes return HTTP 200.
- **Consistency**: shared `formatCurrency` used across 10 component files; shared DeltaIndicator/
  KpiStatCard across 18 — currency + green/red delta color-coding is centralized, not ad hoc.
- **Scope-following**: proven per-page throughout the session (real two-advisor screenshots on the
  flagship pages; useScopedAdvisor / ShellContext everywhere else).

============================================================================================
## SECTION 9 RUN COMPLETE — Phases 0-7 all done.
## Phase 4 = all 14 page rebuilds. Phase 5 = Revenue Trend Explorer (Fable). Phase 6 = RAG
## multi-format corpus + complete .env.example. Phase 7 = closing verification passed.
## Two Fable-5 delegations this session: RL learning-state showcase (page 10) + Revenue Trend
## Explorer (Phase 5). Every page: real backend logic, tsc clean, 0 console errors, screenshot,
## committed + pushed (origin in sync). Genuine new features shipped: manager-assigns-task CRUD
## with AI read-path, What-If save-as-recommendation, RL weight-trajectory showcase.
## Known standing caveats (unchanged, documented): mock graph upserts are in-memory (reset on
## backend --reload/restart); live TigerGraph query INSTALL still unverified on this 2-core box
## (Phase 2/3 C++ compile limit); mock-LLM output carries a deterministic tag that FormattedAnswer
## strips on the AI-heavy pages (real Azure/Claude output has none).
============================================================================================
Coaching&Reviews[manager-task CRUD] → CRM Activities → What-If[save-as-rec] → Predictions[methodology
depth] → Opportunities&Recs[**RL learning-state = delegate to Fable**] → Rec ROI → AI
Assistant+Knowledge → Feature Lab → Explainability), then Phase 5 (Revenue Trend Explorer = **Fable**),
Phase 6 (RAG corpus + .env.example), Phase 7 (closing verify).
REUSABLE now: `AiInsightSummary`/`AiCoachingCard` components + `structured_insight_coaching()` +
`similar_entities()` + `/insights-coaching/generate` — use these on Dashboard & Client 360 rebuilds.
DELEGATION NOTE: the named `fable-architect` agent type is NOT registered; delegate the 2 remaining
Fable items via a general-purpose subagent with `model: "fable"` (as done for Phases 2 & 3).
Servers running: backend :8000 (mock, --reload), dev frontend :3000. Ports 8000/3000 Public.

## Session 9 — 2026-07-05 — SECTION 11 START (real ML/DL/GNN/RL/FL)
Git sync verified before starting: origin/main == HEAD == 90 commits, tip 5d32cb4 (1 unpushed
commit `5d32cb4` was found and pushed). 12 architecture posters confirmed in docs/spec/architecture/.
Section 10 stays DEFERRED. Model routing: main thread Opus; Fable-designated items (11.1 model/
training approach, 11.3 FL design, 11.5 eval-harness design) delegated via general-purpose subagent
with model:"fable" (named fable-architect type still not registered — same proven workaround).

### 11.1 FIRST CHECK — feedback/outcome data variety (gates real-label training) — DONE
Inspected the on-disk labeled data that fresh-boot training would use
(docs/tigergraph_foundation/data/sample/vertices/):
- **Volume:** 36 feedback events, 36 outcome events, 36 learning signals (thin — anticipated by the
  honest small-data rule; fix = train at household/transaction level, hundreds–thousands of samples).
- **Feedback ACTION variety GOOD:** ACCEPT 8 / COMPLETE 7 / DEFER 7 / NOT_RELEVANT 7 / REJECT 7;
  reason_code 5 distinct values.
- **Learning-signal FAMILY variety INADEQUATE (the real gap):** all 36 signals are a SINGLE family
  `CRM_EXECUTION` (signal_json), reward 24×(+1.0)/12×(−0.5), action collapsed to ACCEPT/REJECT only.
  Cannot learn cross-family success/failure distinctions from one family.
- **Outcome variety INADEQUATE:** outcome_type = REVENUE_IMPACT for all 36; outcome_value = 24 zero /
  12 positive — **no negative-impact outcomes**. 11.3's fine-tuning explicitly requires a mix of
  successful AND unsuccessful (completed-with-negative-impact = negative label).
- **Recommendations:** recommendation_type = NEXT_BEST_ACTION for all 120; action_text has 3 latent
  families (CRM follow-up ×60, concentration/product-fit ×30, relationship-growth ×30) — so family
  structure EXISTS in the recs, but the learning signals only ever labeled CRM_EXECUTION.
- **Dormant RandomForest confirmed:** app/prediction/prediction_engine.py trains on a SYNTHETIC
  rank-heuristic target (`_synthetic_target`, rev/nnm/managed/crm .rank(pct=True) blends), NOT real
  labels — confirms 11.1's "promote dormant model + replace synthetic target with real labels" premise.

**Decision (routing the gap correctly, respecting 11.x order):**
1. The advisor/household RISK labels the RandomForest needs (REVENUE_DECLINE_RISK, AGP_OFF_TRACK_RISK,
   household churn) can be derived from data that ALREADY exists — 36-month revenue series + 960 AGP
   KPI measurements — WITHOUT the feedback expansion. So 11.1 model training is NOT blocked.
2. The family-varied / negative-impact OUTCOME expansion is a **11.3 (FL) prerequisite**, not an 11.1
   blocker — will be done as designed under 11.3 (extend the sample-data generator, guardrail: never
   mutate anchored advisor figures A001/A020/etc.).
Next: delegate 11.1 model/training-approach design to Fable (ModelClient adapter, which models, real-
label derivation at household/txn level, SHAP, GRU forecast, Isolation Forest, GDS algos, TigerGraph-
native vs deterministic vector storage, model registry), then implement on main thread with real metrics.

### 11.1 DESIGN — delegated to Fable 5 (general-purpose subagent, model:"fable") — DONE
Design doc: docs/section11/11_1_model_design.md. Grounded in real repo/data (cited file:line); Fable
independently measured label prevalence on the real CSVs. 11 commit-sized units (§12). Recommends
XGBoost over the dormant RF; household×cut training level (n≈2159) per the honest small-data rule;
deterministic tier never deleted (real mode falls back per-type via a registry quality gate, so it can
never regress today's endpoint). Installs needed: torch-geometric only (done). Top risks: live-TG on
2 cores (all fallback-first, time-boxed), AGP label leakage (exclusion list + AUC>0.97 tripwire),
churn rarity 3.8% (class weight + PR-AUC gate). NOTE: earlier "xgboost/shap missing" import check was
transient — re-verified installed; numpy 2.5→2.4.6 downgrade (shap→numba) is benign (full stack + backend import OK).

### 11.1 COMMIT 1/11 — ModelClient adapter skeleton + registry — DONE (4bc726d)
- app/ml/client.py: ModelClient Protocol + DeterministicModelClient (score_risk raises
  ModelUnavailableError → live scorecard unchanged; real seasonal-naive forecast) + RealModelClient
  skeleton (registry-gated; raises until artifacts land) + get_model_client()/reset. Heavy imports lazy.
- app/ml/registry.py: JSON registry (metrics/metadata only), atomic upsert, serves() precedence gate.
  models/registry.json committed; models/artifacts/ gitignored (+.gitkeep).
- settings + .env.example: MODEL_CLIENT_MODE (default deterministic) / VECTOR_CLIENT_MODE / ML_ARTIFACTS_DIR
  / ML_TIME_BOX_MINUTES. Verified: backend boots 36 routes; both modes fall back to scorecard (no
  live endpoint changed yet).

### 11.1 COMMIT 2/11 — real-label dataset builders — DONE
- app/ml/training/datasets.py: household×cut frame (6 cuts 2024-08…2025-11, $500 activity floor) with
  20 leakage-safe features + REVENUE_DECLINE (rev(t,t+6m]<0.85×trailing) + CHURN (<0.70×) labels; AGP
  frame (960 KPI measurements → advisor via progress→enrollment→advisor edge traversal) with advisor
  behavioral features (from raw txns, NOT attainment-derived — status excluded) + kpi one-hot, label
  status==OFF_TRACK. Read-only over foundation CSVs (no upsert, anchors untouched).
- Prevalence report REPRODUCES Fable's independent measurement EXACTLY: n=2159 / decline 0.2663 /
  churn 0.0384 (83 pos) / AGP 960 @ 0.6396. Anti-leakage temporal-wall check (rule 1): 60 rows rebuilt
  from a hard-filtered (<cut) transaction frame → 0 feature mismatches. ~15-22s runtime.

### 11.1 COMMIT 3/11 — train 3 XGBoost classifiers (real metrics, honest gates) — DONE
- app/ml/training/classifiers.py + scripts/train/{train_revenue_decline,train_household_churn,
  train_agp_off_track,run_all}.py. XGBClassifier (hist, §2 baseline config). Temporal split for the
  two revenue models (train cuts 2024-08…2025-05, test 2025-08 & 2025-11); GroupShuffleSplit-by-advisor
  for AGP. Prints ROC-AUC/PR-AUC/Brier/precision@decile/5-bin calibration. Quality gate + AUC>0.97
  leakage tripwire enforced; artifacts→models/artifacts/*.joblib (gitignored), metrics→models/registry.json
  (committed). Each script asserts anchored A001 (revenue_ltm 387293.22 / aum 10018200 / nnm_3m 102080)
  intact — passed on every run.
- **REAL results (honest, NOT tuned to pass):**
  - revenue-decline-xgb: test ROC-AUC **0.7755** ≥0.65 → **gate PASSED, serves()=True** (calibration sane).
  - household-churn-xgb: PR-AUC 0.0117 < floor 0.0208 (3× base) → **gate FAILED** — rare-positive
    (test base rate 0.7%); by design does NOT serve, falls back to scorecard. Card names the proxy nature.
  - agp-off-track-xgb: ROC-AUC 0.6347 < 0.65 → **gate FAILED** (honest near-miss). Made ONE
    design-sanctioned improvement (enriched with the advisor's real Feature_Catalog behavioral features
    per §3.2, all attainment-/status-derived cols excluded incl. revenue_at_risk_estimate → 0.6239→0.6347);
    did NOT tune further to game the gate. Stays gate-failed → live AGP prediction stays on the scorecard.
  - Net: only REVENUE_DECLINE_RISK promotes to the live model path at commit 4; the other two honestly
    fall back. serves() verified: revenue-decline True, churn/agp False. Backend boots 36 routes.

### 11.1 COMMIT 4/11 — live-path promotion + real SHAP + retire dormant path — DONE
- app/ml/real_scoring.py: loads the XGB artifact, scores each of an advisor's households as-of the
  latest month, revenue-weights P(decline)→0-100 advisor score, TreeSHAP → additive signed-point
  contributions (score≈base_value+Σ signed_points) in the EXACT {feature,value,points,why}+direction
  shape the frontend consumes. Rich methodology_patch (pipeline, base_value, additivity, households_scored,
  training_metrics, caveats).
- app/prediction/service.py: predict_revenue_decline / predict_agp_off_track now try the real ModelClient
  first, fall back to the (unchanged) scorecard on ModelUnavailableError. Result schema untouched; methodology
  carries served_by (+fallback_reason). Deterministic mode → always scorecard.
- **Retired the dormant synthetic-label path** (Section 0B "no just-in-case duplicates"): repointed
  app/ai/chat/context_assembler.py off app/services/prediction_service.py onto PredictionRepository
  directly (read-only list_predictions), then deleted app/services/prediction_service.py +
  app/prediction/{prediction_engine,feature_matrix_builder,tigergraph_prediction_linker}.py. Kept
  prediction_repository.py (still used) + models/predictions.py. Fixed the now-inaccurate "RandomForest"
  methodology string → XGBoost.
- **scripts/verify_contributions.py** (evidence → docs/section11/evidence/contributions_before_after.json):
  BEFORE (scorecard) A001 16.7 / A020 15.9 vs AFTER (XGB+TreeSHAP) A001 29.2 / A020 48.1 — real per-advisor
  SHAP with direction, base 29.6, schema-identical between modes (asserted), synthetic-label RF reference
  captured once before deletion (degrades gracefully after). Live predict_advisor(A020) real mode:
  REVENUE_DECLINE served_by=revenue-decline-xgb v1.0 (48.1); AGP served_by=scorecard (56.8, matches anchor).
  Backend boots 36 routes; ChatContextAssembler imports clean.

### 11.1 COMMIT 5/11 — household churn surface (honest, gate-aware) — DONE
- real_scoring.household_churn(advisor_id): loads the churn XGB artifact, scores each of the advisor's
  households, returns per-household propensity+band + the model's real quality_gate/caveat. ModelClient
  gained household_churn() (deterministic → not-available note; real → real per-household scores).
  New route GET /predictions/household-churn/{advisor_id}.
- Advisor 360 households table: new "Churn Risk" column (elevated=red/watch=amber/stable=teal badge with
  propensity %). Because the churn model is BELOW its serving gate, the column shows an explicit
  "Indicative only … PR-AUC 0.0117 below the gate 0.0208 … not a production score" caveat banner — honest
  by construction, never presented as a served number. .env set MODEL_CLIENT_MODE=real (gitignored) so the
  app serves the trained models locally.
- Verified live (real mode): A020 revenue-decline served_by=revenue-decline-xgb v1.0 (48.1); A001
  household-churn 6 real per-household propensities, gate=failed/served=false. Frontend tsc PASS; Playwright
  0 console errors; Churn Risk column + caveat render. Screenshot docs/qa_screenshots/s11-churn.png.
- NOTE: /adapters/status does not yet report the model tier — added in commit 11 (Admin Model Registry tab).

### 11.1 COMMIT 6/11 — GRU revenue forecast with uncertainty band — DONE
- app/ml/real_forecast.py (torch): GRUForecaster (1-layer, hidden 32, input [z-log1p-rev, sin(m), cos(m)])
  + forecast_series (6-mo autoregressive rollout, empirical per-horizon residual-quantile band, per-advisor
  norm stats from artifact). app/ml/training/forecast.py trains shared model over 60 series × 36 mo, validates
  a 6-mo rollout on months 30-35 vs TWO mandatory baselines. Serves only if it beats seasonal-naive, else
  the deterministic seasonal-naive baseline serves (registry gate).
- **Real result: GRU sMAPE 0.0810 BEATS seasonal-naive 0.1184 and ma3 0.0827 → gate passed, served.**
  Trained in 1.4s / 113 epochs (well under the time-box). Artifact revenue-forecast-gru.pt (gitignored).
- Endpoint GET /predictions/forecast/{advisor_id}; RealModelClient.forecast_series wired (deterministic mode
  → seasonal-naive baseline). Frontend: new components/charts/revenue-forecast-chart.tsx (Recharts composed:
  actual line + dashed GRU p50 + p10-p90 band area + baseline-comparison footer), added to Predictions page.
- Verified: tsc PASS; Playwright 0 console errors; forecast chart + real XGBoost SHAP prediction cards render
  (A001 revenue-decline served_by XGBoost 29.2, AGP scorecard fallback 25.8). Screenshot s11-forecast2.png.
  (Backend must run as a harness-managed bg process — `nohup … &` gets reaped in this env.)

### 11.1 COMMIT 7/11 — classical GDS algorithms (PageRank + Louvain) — DONE
- app/ml/graph_algorithms.py (networkx over FoundationGraphStore — NO live-TG INSTALL needed):
  PageRank over the referral/book graph (advisor↔household↔referral↔opportunity↔product edges, 844
  nodes / 1140 edges — products/opps act as shared hubs so advisors are connected) → "Referral Network
  Position" (percentile + tier); Louvain over an advisor kNN graph (k=5 cosine over embeddings) → "Peer
  Communities" with per-cohort distinguishing features (top-3 by |z| vs firm mean). Persists to a new
  graph_metrics SQLite table. Each algorithm serves ONE named screen (no algorithm without a purpose).
- Endpoints: POST /graph-insights/recompute, GET /graph-insights/referral/{id}, /communities (new router).
- **Real results:** A020 "strong referral hub" p86.7 vs A001 "connected" p50 (degree 12 each); 7 discovered
  peer communities (sizes 6-13) with interpretable distinguishing features.
- UI: Referral Network Position card on Advisor 360; Peer Communities card on AGP (current advisor's
  community highlighted). Verified: tsc PASS; Playwright 0 console errors; screenshots s11-referral.png,
  s11-communities.png. NOTE: graph_metrics is runtime SQLite state — POST /graph-insights/recompute
  populates it (cards hide gracefully until then). TG-native GDS (Featurizer.installAlgorithm) documented
  as the bigger-box fallback, same honest pattern as every adapter.
- Ops note: run the backend from the repo root (CWD-relative data paths); `--app-dir` fixes imports but
  not CWD, so relative foundation-data paths fail → empty graph.

### 11.1 COMMIT 8/11 — GraphSAGE embeddings (real GNN, Tier 2) — DONE
- app/ml/gnn.py (torch_geometric): homogeneous GraphSAGE (2-layer SAGEConv 5→64→32, node-type as
  feature) trained SELF-SUPERVISED via link prediction (serves+owns edges, 10% held out, negative
  sampling) over the real FoundationGraphStore graph (1140 nodes: 60 advisor / 360 household / 720
  account; 1080 train edges). scripts/train/train_graphsage_embeddings.py.
- **Real result: held-out link-prediction ROC-AUC 0.6850 ≥ 0.6 gate → passed. Trained 0.9s / 50 epochs**
  (far under the time-box). 32-dim output embeddings persisted to a dedicated gnn_embeddings SQLite table
  (isolated from the existing dim-8 deterministic pipeline so nothing breaks). Registry entry records
  gnn_tier_ran=tier2-local-pyg + the honest Tier-1 caveat (pyTigerGraph[gds] neighborLoader unverified on
  this 2-core box — live edge load stalls).
- **Louvain Peer Communities upgraded automatically to GNN vectors** (graph_algorithms._all_advisor_embeddings
  now prefers gnn_embeddings): community_embedding_source=graphsage-v1, 6 detected communities (was 7 on
  deterministic vectors). Verified. Backend imports clean (37 routes). No frontend change needed — the
  Peer Communities card (commit 7) transparently reflects the improved vectors.
- Tiers per §7: Tier 1 (pyTG[gds]) documented-but-unverified (hardware); Tier 2 (local PyG) RAN and serves;
  Tier 3 (deterministic projection) remains the final fallback.
- **QUALITY FIX during commit 8/9:** first GNN pass gave advisor embeddings that collapsed (all cosine≈1.0)
  because advisor nodes had only generic structural features. Per §7 (advisor nodes carry their real
  Feature_Catalog values) enriched node features with 4 z-scored per-type discriminative slots
  (advisor: revenue_ltm/aum_total/nnm_3m/peer_gap). Result: link-pred ROC-AUC 0.685→**0.9234**, and advisor
  similarity now differentiates (A001→A002 0.96/A008 0.92; A020→A019 0.98/A013 0.93 — distinct neighbours).

### 11.1 COMMIT 9/11 — VectorClient adapter (graph-entity vectors) — DONE
- app/ml/vector_client.py: VectorClient Protocol (upsert_embeddings/search/get/describe), LocalVectorClient
  (SQLite gnn_embeddings + brute-force cosine — the deterministic default, correct at 1.1K vectors),
  TigerGraphVectorClient (native EMBEDDING/HNSW/vectorSearch; delegates to local until support is verified),
  VECTOR_CLIENT_MODE=local|tigergraph. Chroma (RAG docs) untouched/out of scope.
- gnn.py refactored to persist through get_vector_client().upsert_embeddings (adapter discipline).
- GET /graph-insights/similar/{entity_type}/{entity_id} — nearest entities by GNN embedding cosine.
- scripts/check_tg_vector_support.sh: empirical, 20-min-time-boxed TigerVector EMBEDDING-support probe;
  honest UNVERIFIED outcome on this box (same live-TG limit) → local stays the working default, cutover
  env-only on adequate hardware. NOT run live (container Exited; hardware limit already established Phase 2/3).
- Verified LIVE: GET /graph-insights/similar/ADVISOR/A020 → A019 0.98/A013 0.93/A026 0.93/A027 0.90 via
  VectorClient (backend=local). 1140 vectors dim 32. Backend imports clean (37 routes).

### 11.1 COMMIT 10/11 — Isolation Forest anomaly + Activity Pattern Review — DONE
- app/ml/anomaly.py: IsolationForest(200 trees, contamination 0.05) at household level over 6 OWN-HISTORY-
  relative features (recent-rev z vs own 12mo, largest-tx vs own median, tx-frequency ratio, slope break,
  recency vs own gap, single-tx share). Segment/AUM EXCLUDED so wealth level can't drive a flag.
  scripts/train/train_anomaly_detector.py. ModelClient.anomaly_scores wired.
- **Real result: 360 households, 18 flagged = exactly 5.0% (contamination). Card states the false-positive
  expectation out loud.** activity_review(advisor) returns care-framed flags: "Unusual activity pattern —
  review suggested" (never "vulnerable"/"suspicious"), top own-history signals, "Statistical flag, not a
  determination" disclaimer + "own pattern, never a peer/wealth comparison" note.
- Endpoint GET /predictions/activity-review/{advisor_id}. Advisor 360: amber/slate care-framed "Activity
  Pattern Review" card (shows ONLY when the advisor has flagged households; capped at ~5% by construction).
- Verified LIVE: /predictions/activity-review/A042 → H0247 flagged (recent_rev_zmax 2.415). Card hides for
  unflagged advisors (A001 screenshot s11-anomaly.png, 0 console errors) — honest. tsc PASS. The 6 binding
  non-alarmist presentation rules (§9) are honored in the copy + styling (pattern-not-person, amber-not-red,
  evidence attached, explicit uncertainty, human disposition, FP expectation stated).

### 11.1 COMMIT 11/11 — Model Registry tab in Admin + model tier in /adapters/status — DONE
- Backend: new /admin/models + /admin/models/{name} routes (read registry). /adapters/status now reports
  the ModelClient tier (model_client_mode, tier, registered count, serving list) + vector_client_mode.
- Frontend: AdminHealthWorkspace gained a System Health | Model Registry tab switch (lightweight, no new
  dep) + a "Model Client (11.1)" adapter card on the health tab. Model Registry tab = table (name /
  algorithm / trained / primary metric / serving-or-gated badge) with a click-to-expand model card
  (algorithm, label, training data, split, metrics, features, caveats banner).
- Verified LIVE + Playwright: /admin/models → 6 models, 4 serving; Admin Model Registry tab renders all 6
  with honest badges (revenue-decline-xgb roc_auc 0.7755 serving, graphsage-v1 0.9234 serving,
  revenue-forecast-gru sMAPE 0.081 serving, activity-anomaly-iforest serving; agp-off-track-xgb 0.6347 +
  household-churn-xgb 0.0117 GATED/fallback). tsc PASS; 0 console errors (fixed a React key warning).
  Screenshot s11-model-registry.png.

============================================================================================
## SECTION 11.1 COMPLETE — real model tier (ModelClient adapter) end to end.
## 11 commit-sized units, all with REAL metrics + honest gates (no tuning to pass):
##  - XGBoost REVENUE_DECLINE_RISK promoted to the LIVE /predictions path with real TreeSHAP
##    contributions (ROC-AUC 0.7755); dormant synthetic-label RandomForest retired.
##  - Household churn (gated → indicative), AGP off-track (gated → scorecard fallback) — honest.
##  - GRU revenue forecast with uncertainty band (sMAPE 0.081, beats seasonal-naive/ma3).
##  - Classical GDS: networkx PageRank (Referral Network Position) + Louvain (Peer Communities).
##  - Real GNN: PyG GraphSAGE link-prediction (ROC-AUC 0.9234), 32-dim embeddings via VectorClient.
##  - Isolation Forest anomaly (Activity Pattern Review, care-framed, 5% flags).
##  - Model registry + model cards in Admin; deterministic tier NEVER deleted (per-type fallback).
## Every model: real training script, real printed metrics, registry entry, honest quality gate
## (2 of 6 correctly DON'T serve). Anchored advisor figures (A001/A020/F001) asserted intact on
## every training run. Adapter discipline: MODEL_CLIENT_MODE / VECTOR_CLIENT_MODE, heavy imports
## isolated to app/ml/real_*.py + app/ml/training/ + app/ml/{gnn,anomaly,graph_algorithms}.py.
## Fable-designed (general-purpose subagent, model:"fable"): the full 11.1 model/training approach
## (docs/section11/11_1_model_design.md). Next Section-11 items: 11.2 RL formalization → 11.3 FL
## (feedback loop, needs outcome-variety data expansion) → 11.4–11.8, 11.11.
============================================================================================

## Session 9 (cont.) — SECTION 11.2 — RL formalization — DONE (main thread / Opus)
Formalizes the ALREADY-VERIFIED feedback loop as a documented contextual bandit; does NOT rebuild it
(per 11.2). Every value read from the live ACTION_SIGNALS + the ranking/update clamp — nothing changed.
- Backend: FeedbackLearningService.bandit_spec() — state (advisor 33-feature snapshot), actions (recommendation
  families = arms), reward (base_reward ACCEPT 0.6/COMPLETE 1.0/MODIFY 0.3/IGNORE -0.1/REJECT -0.5 + outcome
  adjustment, clamp [-1,1]), policy (rank_priority = base_priority × family_weight), update (w ← clamp(w +
  δ_action, 0.5, 1.5); δ ACCEPT +0.05/COMPLETE +0.10/MODIFY +0.02/IGNORE -0.02/REJECT -0.08), exploration
  (greedy; clamp preserves residual exposure; ε-greedy/UCB = future work). Exposed via /feedback-learning/
  learning-state AND folded into /impact-trend (additive `bandit` key).
- Frontend: LearningStateShowcase (9.5 component) gained a "Formalism · Contextual Bandit" panel above the
  existing weight-trajectory replay — fed in, not duplicated. Replay viz already existed from 9.5.
- Verified LIVE: /feedback-learning/impact-trend → bandit spec + 18 real events; Playwright: bandit panel +
  weight-trajectory (CRM Execution→1.50 / Managed Mix→0.53) render together, 0 console errors, tsc PASS.
  Screenshot s11-bandit.png.
Next: 11.3 FL (outcome-driven learning — needs outcome-variety data expansion first, Fable-designed).

## Session 9 (cont.) — SECTION 11.3 — FL = Feedback Loop (outcome-driven learning) — DONE
NOT Federated Learning (client-corrected). Additive deeper layer on top of the verified bandit (11.2):
recorded recommendation outcomes fine-tune the GNN's embeddings so peer/situation evidence stops
pointing at combinations that failed. Fable-designed (docs/section11/11_3_fl_design.md); 7 commit-sized
units. graphsage-v1 + the bandit loop stay intact; -ft serves only past a link-pred retention gate.
- **Commit 1 (Part A data):** expand_outcome_variety_v1_3.py — +144 (feedback,outcome,learning_signal)
  triples across ALL 3 families with a real success/failure mix incl. 18 genuinely-negative outcome_value
  rows ("completed but it hurt"). 7 files 36→180, manifest 7/7. validate_package PASS (155,954 rows);
  idempotent; anchors intact.
- **Commit 2:** gnn.py saves graphsage-v1.pt state_dict; registry.active_embedding_model(); VectorClient
  model_name param + ?model= on /graph-insights/similar (before/after inspection).
- **Commit 3:** app/ml/fl_pairs.py — chain-walk pair builder (P1 same-family-positive pull / P2 pos-vs-neg
  push / P3-P4 relationship), legacy vocab map, seeded 20% holdout. 180 events → 1347 pairs, deterministic.
  Honest data note: MANAGED_MIX/RETENTION recs target few households → thin advisor pairs; CRM + relationship
  pairs carry the signal.
- **Commit 4:** app/ml/fl_finetune.py — L = L_linkpred + 0.5·margin-contrastive (m=0.2, lr 1e-3, ≤20 epochs,
  time-boxed). Persists graphsage-v1-ft (v1 rows PK-immutable) + per-advisor/family affinity for both models.
  Real result: link-pred AUC 0.969→0.953 (retention gate PASSED); separation −0.0215→−0.0175 (right
  direction, tiny — anticipated small-effect case); RETENTION per-family +0.035. active model → -ft.
- **Commit 5:** app/ml/fl_service.py + endpoints POST /feedback-learning/retrain, GET /before-after,
  /outcome-learning. RecommendationService attaches outcome_affinity evidence (always) + bounded ±10%
  confidence modifier (FL_AFFINITY_IN_CONFIDENCE, default true; priority stays bandit-owned). Verified live:
  POST recs/generate/A020 → affinity evidence per rec; affinity real per-advisor (A001 +0.02 / A005 −0.04).
- **Commit 6:** outcome-learning-panel.tsx on the Recommendations page (below the bandit replay): two-layer
  explainer, Run-Feedback-Driven-Retraining button, real metrics, before/after similar-advisor columns +
  rank-move badges, per-family affinity deltas, mandatory amber "small on demo-scale" honesty note. All
  numbers from the payload; tsc PASS; 0 console errors. Screenshot s11-fl-panel.png.
- **Commit 7:** .env.example FL_AFFINITY_IN_CONFIDENCE; Admin Model Registry tab renders graphsage-v1-ft
  automatically ("7 models · 5 serving", -ft serving, separation_after=−0.0175). Screenshot s11-fl-registry.png.
Honesty: v1/bandit/deterministic fallbacks never deleted; -ft gated by AUC retention; small effect shown
truthfully (not tuned); terminology "outcome-driven learning"/"feedback loop" throughout.
Known standing caveats: mock graph upserts in-memory (reset on --reload); run the backend from repo root
(or with absolute FOUNDATION_DIR/SQLITE_DB_PATH) — relative data paths fail under a wrong CWD.
Next Section-11 items: 11.4 temporal KG showcase → 11.5 Eval & Trust (Fable-designed) → 11.6 context
engineering → 11.7 observability → 11.8 MCP layer → 11.11 two-AI-systems labeling.

## Session 9 (cont.) — SECTION 11.4 — Temporal knowledge graph showcase — DONE (main thread)
Surfaces the temporal capability that existed only in fragments. Real point-in-time, no fabrication.
- **Feature Lab point-in-time (part 1):** GET /features/as-of/{id}?as_of=YYYY-MM-DD recomputes the
  advisor's features AS OF a chosen date from the real time-windowed graph facts (persisted as versioned
  FS_<id>_<date>_v2.0). New PointInTimePanel compares an as-of date vs today across 8 tracked features with
  color-coded deltas. VERIFIED real movement: A001 2025-01→2026-07 aum_total $9.06M→$10.02M, managed ratio
  5.6%→11.2%, nnm_3m −$1.6K→$102.1K, revenue_growth 8.91→23.3. Both snapshots computed live.
- **Graph Explorer temporal traversal (part 2):** advisor_neighborhood(as_of) hides entities created after
  the date (creation-date map per vertex type; AI pipeline artifacts generated_at, crm_lead created_date,
  agp_enrollment start_date). GET /graph-viz/neighborhood?as_of=; new "Point in time" selector on the
  Graph Explorer + an indigo "N entities hidden (not yet created)" note. VERIFIED: A001 now 19 nodes →
  2025-06 13 nodes (6 AI-pipeline artifacts hidden — the pipeline "hadn't run yet").
- **Memory Timeline connection (part 3):** explicit temporal-KG framing strip on the Explainability Memory
  Timeline cross-linking to the point-in-time feature snapshots + as-of graph traversal (the episodic record
  over time as one leg of the temporal story).
- Verified: tsc PASS; Playwright 0 console errors on both pages; screenshots s11-pit-features.png,
  s11-temporal-graph.png. Honest caveat: some features are current-state (crm_pipeline) not time-windowed,
  so they don't move across dates — the revenue/AUM/NNM/managed features do.

## Session 9 (cont.) — SECTION 11.11 (Two AI Systems visible) + SECTION 11.5 (Evaluation & Trust) — DONE
### 11.11 (main thread)
- app/api/routers/architecture.py: /architecture/{model-strategy,ai-protections,business-outcomes}. Model
  Strategy = real per-function serving (live registry + adapter modes); AI Protections = honest Top-10
  (7 implemented / 3 partial). Admin gained "Model Strategy" + "AI Protections" tabs.
- Labeling: AI Assistant → "iPerform Coach Q&A Assistant" (reactive); AiContentCard chip → "iPerform
  Insights and Coaching" (proactive); Exec Dashboard KPIs annotated with business outcomes.
- Backend launch made CWD-independent (PYTHONPATH + absolute FOUNDATION_DIR/SQLITE_DB_PATH; evaluation
  router resolves paths via __file__) — the robust fix for the recurring wrong-CWD empty-store issue.
### 11.5 (Fable-designed harness)
- golden_qa.json (v2): 25 Q (20 grounded + 5 refusal), synonym-group matcher. scripts/eval/run_golden_eval.py
  runs the REAL RagGenerationService.answer (== POST /knowledge/ask) on LLM_CLIENT_MODE=claude; deterministic
  scoring (groundedness = point in answer AND evidence; citation = inline [n]+must_cite; refusal = honest
  decline). Fails loudly in mock (exit 1, verified).
- **REAL Claude runs committed (trend): v1 80% → v2 88% pass** after ONE sanctioned calibration (widened
  G02/G04 must_cite to the valid co-retrieved doc). Latest: **groundedness 85%, citation 100%, refusal 100%,
  22/25 pass.** 3 honest FAILs (G05/G06/G12) where Claude declined partial answers — the guard working.
- Read-only /evaluation/runs{,/latest}; Admin "Evaluation & Trust" tab (guard banner, KPI cards, per-question
  expandable point-level evidence, trend chart). tsc PASS; Playwright 0 errors; screenshots.
Next: 11.6 context engineering (RerankClient + memory audit + scope-aware AI, real Claude) → 11.7 → 11.8.

## Session 9 (cont.) — SECTIONS 11.6, 11.7, 11.8 — DONE (main thread)
### 11.6 Context engineering — DONE (real-Claude verified)
- RerankClient adapter (app/llm/rerank_client.py): LocalRerankClient (embedding-cosine proxy, free) +
  CohereRerankClient; RERANK_CLIENT_MODE=local|cohere — the poster's "Context Ranking" step. Context
  assembler retrieves broadly then reranks + prunes to top-K.
- Scope-aware reasoning (real gap closed): non-Advisor scopes consult ScopeRollupService for a REAL
  aggregate; verified REAL CLAUDE — Division D01 "why is revenue lagging?" reasons across 24 advisors
  ($14.7M/$797.5M), names Top (Morgan Hill/Riley Kim) + Needs-attention (Avery Diaz/Jordan Garcia), NOT
  one advisor. Advisor 2-turn continuity: follow-up builds on turn-1 context.
- All 6 poster memory types populated (added SEMANTIC/EPISODIC/PROCEDURAL/PREFERENCE to the enum;
  memory_seeder grounds them in real data; /memory/audit → A001 6/6).
- Visible pipeline: GET /ai-chat/context-trace + ContextPipelinePanel on Explainability (resolved scope →
  retrieved items w/ rerank scores → kept/pruned). tsc PASS; Playwright 0 errors; screenshots.
### 11.7 Observability — DONE
- app/observability/recorder.py: in-process per-LLM-call token/cost/latency (real from Claude/Azure
  response.usage; estimated for mock, flagged) + stage-span traces. LLM clients instrumented.
  GET /observability/{summary,llm-calls,stage-spans}; Admin "Observability" tab. Verified 6 calls / 5349
  tokens / $0.0075 est.
### 11.8 MCP layer — DONE
- app/mcp/tool_registry.py: MCP tool registry (poster shape) with two new families — feature_store
  (get_snapshot/list_features) + model_serving (predict_risk/forecast_revenue/similar_advisors/
  household_churn), 6 tools. GET /mcp/tools + POST /mcp/invoke; MCP Tools card on the Admin Model
  Strategy tab. Verified live: model.similar_advisors A020 → real GNN result (graphsage-v1-ft, A019 0.98).
  (Graph access remains the 9.4 4-tier GraphClient MCP adapter.)

## Session 10 — 2026-07-06 — SECTION 12 (Regression Audit & Critical Fixes) begins
Master order: 12 → 13 → 13B → 10 (remaining) → 14. Main thread Opus 4.8; §13/§13B design → fable subagent.

### 12.1 Executive Dashboard — DONE (verified real before/after)
Root-cause diagnosis: Period + Compare-To were UI-only because `/scope/summary` ignored them (original
never-closed 9.2 gap, not a §11 regression). Hierarchy drill-down "intermittent" = breadcrumb skeleton on
hierarchy-fetch race (data-timing, not logic).
Backend:
- `app/revenue/analytics.py`: added per-business-line prior-year tracking → `revenue_drivers` (YoY per
  category), and a prior-*period* window → `comparison_prior_period` (immediately preceding equal-length).
- NEW `app/scope/dashboard.py` `ScopeDashboardService.dashboard(scope,period,compare_to)`: composes rollup
  totals/status/top+bottom advisors + period-windowed revenue (trend/product-category/channel/drivers/geo)
  + top & bottom markets + peer benchmark (rev/advisor vs firm avg + percentile) + a headline whose delta
  respects Compare-To (Prior Year | Prior Period | Peer Benchmark | None). All real sums/means.
- NEW `app/scope/insight.py` `ScopeInsightService`: scope-level AI Insight (Key Drivers/Watch Outs/What to
  Monitor) DERIVED from the real scope+period numbers; LLM writes only the executive-summary narrative.
- `app/api/routers/scope.py`: `GET /scope/dashboard`, `GET /scope/ai-insight`.
Frontend:
- Rewrote `components/command-center/executive-dashboard.tsx` to consume `/scope/dashboard` (period +
  compareTo from shell). Added Revenue Trend, Revenue by Product Category (donut w/ centered total),
  Revenue Drivers vs Prior Year (green/red YoY bars), Benchmarking vs Peers (bars + firm-avg line +
  percentile), Top & Bottom Markets, AI Insight Summary (grounded, lazy `/scope/ai-insight`), AI Coaching
  (Advisor scope only, from `/advisor/360/{id}/ai`). Renamed "Needs Attention"→"Bottom Advisors", added
  AUM + Why columns. REMOVED the Business Outcomes strip (client-directed). 
- Shell: added `resetFilters()` (scope→F001/Firm, period→LTM, compare→Prior Year) + a "Reset filters"
  button in the filter bar. Firm fallback label set to "Chase Wealth Management" (seed rename pending 12.10).
Evidence: Firm/YTD $22.2M (−0.8% vs Prior Year) → drill Eastern Division + QTD → $1.3M (+19% vs Prior
Year), 24 advisors, division-specific categories/markets/regions, benchmark highlights Eastern. 0 console
errors both. Screenshots s12-1-dashboard-firm.png, s12-1-dashboard-division-qtd.png.
QA tooling: added `frontend/scripts/qa-shot.mjs` (proxies browser API calls to local backend so in-container
Playwright renders real data without the public-URL CORS/auth issue).

### 12.2 Filter bars (audit) + 12.3 Revenue Analytics — DONE
Audit: the filter bar is global (AppShell TopHeader → PersonaScopeSelector), so it renders on EVERY
page; `admin`/`knowledge` legitimately don't scope-follow (system/search pages), all other data pages
consume `useShellContext`/`useScopedAdvisor`. So "Revenue Analytics has no filter bar" was a
misperception — the global bar is present and this page consumes scope + period.
ROOT CAUSE of the real breakage (not a filter issue): several ResponsiveContainer charts hit the known
Recharts "blank measure race" — animation plays at width 0 then never replays after the container
resizes, leaving axes but no marks. This was NOT a §11 regression per se but a latent flaky-render bug
surfaced by page weight. FIX: added `isAnimationActive={false}` to every chart mark across
revenue-analytics-workspace (trend Area, channel Bar, division Bar), revenue-trend-explorer, and the
shared chart components (product-mix, kpi-target-actual, revenue-trend-chart, scope-child-bars,
whatif-impact-bars, agp-cohort-bars, peer-radar, roi reward Area + weight Bar). Verified: Revenue Trend,
Revenue by Division ("Revenue by scope"), and Revenue Trend Explorer all render marks now (were blank).
12.3 real US map: replaced the tile-grid `RevenueStateMap` cartogram with a REAL US choropleth —
`d3-geo` geoAlbersUsa + `topojson-client` + locally-bundled `us-atlas/states-10m.json` (offline, no
runtime fetch), FIPS→USPS join to the real by-branch-state revenue, sequential blue fill, hover
tooltip, legend gradient, ranked list beside. Client-directed "not some boxes with state names" met.
Added deps: d3-geo, topojson-client, us-atlas (+ @types). Evidence: s12-3-revenue-real-map.png (0 errors),
s12-3-revenue-charts-fixed.png.

### 12.4 Advisor 360 — DONE
- Referral Network Position (centrality) clarity: was a bare "connected — 12 entities (top 50%)" line.
  Now shows Connections + Firm-Percentile stats AND a plain-language interpretation tiered by percentile
  (top-15% → "strong mentor candidate, anchors AGP pairing"; ≤40% → "above-average hub"; else "growth
  opportunity"), plus a footnote on what PageRank centrality means and why it matters. (Diagnosis: original
  never-closed gap — the §11.1 purpose existed in plan but never reached UI copy.)
- "Households · Accounts · Activities" section was a households-only table. Converted to a real tabbed
  section: Households (existing table + churn), Accounts (real per-account split: name, color-coded type
  badge IRA/MANAGED/TRUST/BROKERAGE, status, value — 12 accounts), Activities (real CRM activities: date,
  type, subject, status, next action, sentiment). Book-by-Account-Type donut + Households-by-Segment
  breakdown already existed and stay. Evidence: s12-4-advisor360-after.png, s12-4-advisor360-accounts-tab.png.
- Note: the two "empty AI boxes" seen pre-fix were just skeleton/load-timing (the /advisor/360/{id}/ai
  endpoint returns 200 in 0.5s); with an adequate wait both AI Insight + Coaching cards render fully.

### 12.5 CRM Activities funnel — DONE (design pass, logic unchanged)
Redesigned `components/charts/crm-stage-funnel.tsx` from flat centered rectangular bands to a proper
tapering SVG funnel: connected trapezoid segments (each band's top edge meets the previous), sequential
blue ramp (dark→light), real per-stage count + $ amount inside each band, stage-to-stage conversion %
on the right, Won/Lost outcome chips below. Width ∝ open opportunity count (floor keeps empty stages
readable); honest to sparse per-advisor data. SVG so it never hits the measure-race. Evidence:
s12-5-crm-funnel-after.png (0 errors).

### 12.6 Explicit advisor-selector on 4 pipeline pages — DONE
Diagnosis: scope-following is NOT regressed — all 4 pages use `useScopedAdvisor` and re-fetch correctly
(verified live: Predictions A001→A020 via the new selector changed Highest Risk 29.2→56.8, Rev-Decline
29.2→48.1, AGP 25.8→56.8, snapshot FS_A001→FS_A020, feature contributions, forecast, AND the hierarchy
breadcrumb synced to Western Division › Phoenix Metro › Riley Adams). The complaint was discoverability —
the breadcrumb doesn't read as an advisor picker. FIX: new reusable `components/status/advisor-selector.tsx`
(fetches /advisor/list, shows the currently-resolved advisor even under a rollup scope, sets shell scope to
the chosen advisor so every scope-following page re-fetches). Added to Predictions, Opportunities &
Recommendations, Feature Engineering Lab, Explainability Explorer headers. Evidence: s12-6-predictions-a/b,
s12-6-recommendations/featurelab/explainability .png (all 0 errors).

### 12.7 Feature Engineering Lab re-verify (post-§11) — DONE (verification, no code change)
Live cross-check of the rendered page vs. direct backend calls for A001: revenue_ltm 387293.22,
aum_total 10018200, managed_revenue_ratio 0.1123, household_count 6, account_count 12,
revenue_growth_3m_pct 23.3, agp_risk_score 19.1, advisor_degree_centrality 0.39, snapshot
FS_A001_20260703_v2.0 — ALL match the page exactly. Similar advisors real
(deterministic-feature-projection, honestly labeled "not a trained GNN"): A004 0.8575→page 0.858,
A007 0.8444→page 0.844, with real reason_features. Visual lineage diagram (FeatureLineageDiagram)
wired (feature rows clickable → source→feature flow). Point-in-time snapshot compare works
(2025-01-31 vs today, both computed live). No regression from §11. Evidence: s12-6-featurelab.png.

### 12.8 Opportunities & Recommendations — minimum visible feedback — DONE
Diagnosis: clicking a feedback button posted to /feedback-learning/submit (real reward + weight update)
but produced NO visible change — the rec's status didn't update, and the summary counts came from
/feedback-learning/impact-trend whose totals are STATIC (seeded history, don't increment on submit).
FIX (minimum per 12.8; full state machine is §13): (1) optimistic per-rec status via `actedStatus` map →
a colored ● ACCEPTED/COMPLETED/IN PROGRESS/IGNORED/REJECTED badge on the card; (2) overlay the session's
actions onto the summary counts so Accepted/Completed/In-Progress/Rejected visibly increment on click;
(3) richer "WHAT CHANGED" note naming the rec + new status + the learning effect; re-fetch queue + impact
on submit. Verified live: clicked ACCEPT on "Accelerate the stalled CRM pipeline" → card shows ●ACCEPTED,
Accepted count 14→15, note "You accepted … → status ACCEPTED. Future CRM_EXECUTION … weight 1.44 (was
1.39)." Buttons NOT disabled yet (deferred to §13 by design). Evidence: s12-8-recs-after-accept.png.

### 12.9 Admin Health/Observability Next.js errors — DIAGNOSED (not reproducible) + hardened
Real evidence: drove /admin through ALL 6 tabs (System Health, Model Registry, Model Strategy, AI
Protections, Evaluation & Trust, Observability) via Playwright capturing every console message, pageerror,
requestfailed, and ≥400 response, plus checked the nextjs-portal dialog. Result: 0 console errors, 0 failed
app requests, empty error portal. All admin endpoints return 200 (/adapters/status, /observability/*,
/architecture/model-strategy, /admin/models, /evaluation/runs/latest). The two reported errors DO NOT
reproduce in the current build — most likely already resolved by the §11.11 CWD-independence fix (which
cured the recurring wrong-CWD/empty-store issue that surfaced as render errors). Defensively hardened 3
latent render-throw hazards matching the reported class (would throw only on an unexpected endpoint shape):
`lr?.row_count_mismatches?.length`, `status.graph.load_report?.vertex_types/edge_types`, `mcp.tools?.length /
mcp.families ?? {}`. Evidence: qa-admin-diag output (all clean), s12-9-admin-*.png.

### 12.10 Navigation / branding — DONE
1. Firm rename: changed the seed Firm vertex name in docs/tigergraph_foundation/data/sample/vertices/
   phx_dm_firm.csv (F001) "Northstar Wealth Management" → "Chase Wealth Management", and the firm-branded
   product display names (phx_dm_product.csv, "Northstar X" → "Chase X"; IDs/figures unchanged). Verified
   after backend reload: /hierarchy/tree firm label = "Chase Wealth Management"; it now flows through the
   breadcrumb, Exec Dashboard title ("Chase Wealth Management Overview"), AI Insight header, and the nav.
   0 remaining "Northstar" strings in runtime data/. No anchored numeric figures touched (display strings
   only). NOTE: backend must be restarted with `setsid python3 -m uvicorn ...` (detached) — a plain
   nohup in a compound bash command got SIGHUP'd on shell exit.
2. Bottom-left nav element: redesigned the ambiguous "{persona} / {scopeType}·{period}" block into a
   clearly-labelled "ACTIVE VIEW" card with Persona / Scope (label · type) / Period rows. Evidence:
   s12-10-branding.png (0 errors).

## SECTION 12 COMPLETE (12.1–12.10). Pushing at section boundary.

## SECTION 13 — End-to-End Stateful Recommendation Lifecycle — COMPLETE (fable-designed, Opus-implemented)
Design: docs/design/section13_lifecycle_design.md. Implemented in 11 commits.
- **13.1 State machine**: new `app/recommendations/lifecycle.py` (SQLite = durable status authority since
  the live generate path re-upserts vertices with a transient status). Enum += IN_PROGRESS/MODIFIED.
  OPEN→ACCEPTED→IN_PROGRESS→COMPLETED / REJECTED / IGNORED / MODIFIED. Transitions persisted with
  timestamp+actor (phx_dm_local_rec_status_transition). Terminal ⇒ allowed_actions=[] ⇒ buttons disabled.
- **13.2 Impact ledger**: phx_dm_local_impact_ledger; on COMPLETED, injects a real
  phx_dm_revenue_transaction (dated 2026-06-30 = last-complete-month-end, so it lands in BOTH the snapshot
  revenue_ltm window AND revenue-analytics trailing-12) linked by NEW edge
  phx_dm_transaction_from_recommendation (schema delta added + structurally validated). Amount = the rec's
  OWN estimated_revenue_impact (structurally enforced, never a parameter). "What changed" note on the rec.
- **13.3 Propagation**: injection (transaction-based screens: Revenue Analytics, Advisor360 trend, rollup
  _comparison) + one-advisor snapshot recompute (snapshot-based: Advisor360 KPIs, Exec rollup totals). NO
  read-time overlay. VERIFIED exact +impact on ALL 3 screens (A005: +$52,110.55 on advisor rev-analytics,
  advisor snapshot revenue_ltm, AND firm rollup — to the cent).
- **13.4 AI awareness**: ChatContextSource.RECOMMENDATION_LIFECYCLE (score 95) + InsightDataCollector
  lifecycle key + memory write on terminal. Context-assembly plumbing VERIFIED (assembled context carries
  "COMPLETED ... +$59,204 impact (transaction TXIMP_...)"). BLOCKER (documented, honest): the real-Claude
  answer-TEXT check needs ANTHROPIC_API_KEY, ABSENT in this session's .env — cannot fabricate a key. The
  data-correctness plumbing is proven in mock; the real-Claude text check runs once the key is added (same
  standing rule as prior sections; the key is gitignored and was present in earlier sessions).
- **13.5 Regeneration**: completed opp excluded from re-issue, surfaced in addressed_opportunities. VERIFIED.
- **13.6 Explainability**: reasoning_trace_id REASON_{rec_id} carried through lifecycle_for + ledger rows.
- **13.2-view / new surfaces (user clarification)**: NEW Impact Ledger page (/impact-ledger, nav "AI" group,
  Receipt icon) — KPI cards + ledger table (rec/family/+impact/tx/note) + expandable lifecycle timeline +
  evidence. Recommendations workspace now fully server-driven (status badge, terminal button-disable, Start
  button, real lifecycle_counts, impact note + "View in Impact Ledger", Addressed section).
- **Learning loop (§11.2/11.3) INTACT**: feedback service still moves the bandit weight in step with every
  status change (verified: accept → weight 1.5); 409 on terminal also stops weight-farming by re-clicking.
- **13.8 verification**: scripts/verify_section13_lifecycle.py — 9 assertion groups, ALL PASSED
  (docs/qa_screenshots/section13/verify_trace.txt). Restart-durability separately verified (replay-report=1,
  ledger + revenue persist across restart). Screenshots: s13-9-recs-complete.png, s13-10-impact-ledger.png.
- **Anchored-figure guardrail honored**: verification ran on NON-ANCHORED A005; A001/A020 untouched. After
  the UI test that completed an A001 rec, A001 was reverted to its anchored 387293.22 (snapshot recompute
  post-restart). Final state: A005 base 406375.14, ledger empty, A001 anchored 387293.22 — pristine; the
  guided scenario (13B) will populate the ledger live.
- **Ops note**: backend must be launched detached (`python3 -m uvicorn ...` as a tracked bg process); plain
  nohup/setsid inside a compound bash command gets SIGHUP'd on shell exit.

## SECTION 13B — Guided End-to-End Story Mode — COMPLETE (fable-designed, Opus-implemented; 13B.3 deferred)
Design: docs/design/section13B_story_mode_design.md. The narration layer over §13's real loop — adds no state, fakes nothing.
- **13B.1 pipeline trace (extends Explainability)**: NEW `GET /explainability/pipeline-trace/{rec_id}` composes the 6-stage
  SYSTEM TRACE (Data→Feature Engineering→Model→Opportunity/Recommendation→Context&Compliance→Delivered Output) from real
  sources; `PipelineTraceBar` renders it above the lineage chain (6 stage cards + proportional bar + real timing basis).
  Added real compliance verdict to the live rec payload (RecommendationComplianceValidator) + real generation stage-timing
  (first producer of observability stage-spans). VERIFIED cross-checks: trace feature revenue_ltm == snapshot, derivation
  impact == rec estimate, compliance status == rec compliance (verify_section13B_story.py ALL PASSED). s13b-4-pipeline-trace.png.
- **13B.2 guided overlay (NEW surface)**: `StoryModeProvider` in AppShell + `StoryOverlay` (bottom-docked) + declarative
  `scenarios.ts` advisor journey (11 steps) + `/story` launch + nav "Guided Story Mode". Drives the REAL app (setScope +
  router.push + data-story-target highlight), runs a REAL accept+complete, and shows live proof chips. VERIFIED end-to-end
  via Playwright: the propagation step proof chip showed "$406,375 → $458,486 (+$52,111) = exactly the impact ✓" with the
  injected transaction visible as a RECOMMENDATION_IMPACT channel. Replayable via NEW same-process reset
  (POST /recommendations/lifecycle/reset/{id} + store.remove_vertex, A001/A020 403-guarded — no restart needed).
  s13b-step01..08 screenshots.
- **13B.4 Business Impact & ROI (NEW Executive surface)**: `/business-impact` — cumulative recorded impact, acceptance/
  completion rates (from new `lifecycle_totals`), impact-over-time, impact-by-family, business-outcome mapping strip, honest
  empty state. VERIFIED empty ($0, links to Story Mode) AND populated ($560,059, 5 acted, 100% acceptance, 80% completion).
  s13b-10-roi-empty.png, s13b-10-roi-populated.png.
- **13B.3 division-leader journey — DEFERRED** (honest scope call given session length): the same StoryStep engine supports
  it as a second scenario entry using existing rollup/coaching endpoints (design §3); not yet added. The two genuinely-new
  surfaces the user required (guided overlay, ROI page) + the pipeline-trace extension are all done and verified. This is a
  clean, additive follow-up — no new backend needed.
- **13B.5 verification**: verify_section13B_story.py ALL PASSED (docs/qa_screenshots/section13B/verify_trace.txt). Real-Claude
  closure step (13B.2 step 10) inherits the §13.4 documented blocker (no ANTHROPIC_API_KEY this session) — the context-assembly
  is proven; the overlay shows an honest note when LLM is mock. Final state: A005/A015 reset to pristine, A001/A020 untouched.

## SECTION 10 (remaining) + SECTION 14 — COMPLETE (with honest scope notes)
### Section 10 — remaining items (re-checked vs what §11-13B already built)
- **Real header icons (flagged "give them real purpose")**: NEW `/search/global` (advisors/households/docs)
  + `/search/notifications` (real feed: AGP off-track / at-risk advisors, overdue CRM follow-ups). Header now
  has a working search box (verified: "riley" → 4 real advisors) + a notification bell with a live count
  (verified: 16 real alerts). Replaced the search-icon-only-routes-to-knowledge + removed-bell (9.2).
- **Already satisfied by §11-13B (not rebuilt, per 10-RESOLUTION)**: anomaly/vulnerable detection (§11.1),
  AGP cohort/mentor/ROI graph-algos + embeddings (§11.1), household churn model (§11.1), the RL/feedback
  learning showcase (§9.5/§11.2/11.3), impact/ROI aggregation (§13B.4 Business Impact page).
- **DEFERRED as scoped additive follow-ups** (honest, given session length): AUM net-flows waterfall on the
  Exec Dashboard; export-any-view-to-PDF/PPT (needs a client-side export lib); household-level next-best-
  product / concentration / review-cadence extensions of §11.1's model tier; §13B.3 division-leader story.
  None require new architecture — all are additive on the now-built foundation.

### Section 14 — final directive: flip to real graph + real LLM, verify boot/serve — DONE
- Set `.env`: GRAPH_CLIENT_MODE=real, LLM_CLIENT_MODE=claude (handover config; `.env.example` documents it).
- VERIFIED boots + serves: health 200 (1ms), /scope/dashboard 200 (~2.8s), /advisor/360 200 (~1s); full
  Executive Dashboard UI renders with real data, 0 console errors (s14-real-claude-dashboard.png). Graph
  reports mode=tiered:real, healthy — the tiered client serves from the seeded store via automatic fallback
  when TigerGraph is unreachable (logs the served tier); point it at a reachable TigerGraph for good latency.
- **CORRECTION to earlier §13.4/§11.6 "blocked on ANTHROPIC_API_KEY" notes**: the key IS present in the OS
  ENVIRONMENT (resolved by settings.anthropic_api_key, len 108) — it was never in the .env FILE, which is why
  the file grep missed it. **Real Claude works.** Verified: /scope/ai-insight returned genuine prose ("Revenue
  declined 7.4% YoY to $35.9M despite healthy net new money of $29.6M…"), and the §13.4 AI-Assistant check on
  a completed A005 rec: real Claude's answer reflects the POST-completion revenue ($486,365 = base $434,254 +
  the $52,110 recorded impact) — i.e. the completed action's consequence IS in the AI's grounding. Honest
  nuance: the impact is reflected in the cited numbers; the explicit "you completed X for $Y" narration is
  partial (the RECOMMENDATION_LIFECYCLE context item is assembled at score 95 but the answer synthesis leans
  on the insight/coaching summary) — a prompt-weighting refinement, not a data/plumbing gap.
- Latency caveat documented in .env.example: for a fast fully-offline local demo keep GRAPH_CLIENT_MODE=mock;
  real mode is for the client's site with their TigerGraph.

## MASTER EXECUTION ORDER (12 → 13 → 13B → 10 → 14) — all sections addressed. Deferred items listed above.

## Session 11 — 2026-07-07 — Remaining deferred items (6-item run, Opus)
Completing the deferred follow-ups. Real Claude available this session (ANTHROPIC_API_KEY set,
LLM_CLIENT_MODE=claude verified: `CLAUDE_OK` smoke test passed). Commit per item.

### ITEM 5 — Household model extensions: next-best-product propensity — DONE
- household churn/attrition ALREADY existed (household-churn-xgb, §11.1) — confirmed registered +
  served via /predictions/household-churn/{advisor}. Not rebuilt.
- NEW next-best-product propensity, reusing the model tier (registry + ModelClient + predictions
  endpoint), NOT a parallel stack:
  - `app/ml/next_best_product.py` — collaborative propensity over the REAL holdings graph
    (advisor→household→account→product→subcategory→category, 2,880 holdings, 8 categories):
    propensity(C) = 0.70·segment_peer_adoption + 0.30·overall_penetration for each not-yet-held
    category. Deterministic + explainable; honest caveat (static holdings, no adoption events).
  - Wired: `ModelClient.next_best_product` on BOTH tiers (data-driven, no artifact) + Protocol;
    `GET /predictions/next-best-product/{advisor_id}`; registry entry `next-best-product-cf`.
  - Evidence: HTTP 200; A001 → 6 households, H0001(AFFLUENT) holds 6 cats, top next-best
    Alternatives (0.68, "68% of AFFLUENT households hold Alternatives; this household does not");
    held vs recommended overlap = ∅; A005 returns different households (real scoping).

### ITEM 1 — AI labeling correction — DONE (verified)
- Per-card chip already literal "✦ AI Generated" (no product name); AI Assistant page/nav already
  "iPerform Coach Q&A Assistant" (commit 8bb6380) — confirmed by audit, no reverts needed.
- Added shared `ProductSystemLabel` + proactive "iPerform Insights and Coaching" page label on
  predictions/recommendations/advisor-360. Evidence: docs/qa_screenshots/session11/predictions_label.png,
  ai_assistant_coach.png; tsc PASS. (NOTE: these frontend files were swept into the item-5 commit
  e77fd3c by `git add -A`; work is committed, just bundled with item 5.)

### ITEM 3 — AUM net-flows waterfall (Exec Dashboard) — DONE
- `app/scope/net_flows.py` AumNetFlowsService + `GET /scope/aum-net-flows`: reconciling AUM bridge
  (Beginning + New AUM − Departures + Market/Organic Growth − Fees = Ending) from REAL monthly
  AUM/NNM snapshots + FEE transactions per in-scope advisor; growth = reconciling residual.
- Frontend `AumNetflowWaterfall` (Recharts stacked-float, zoomed Y-axis) on the exec dashboard.
- Evidence: FIRM $2.065B +20.4M −1.26M +23.5M −10.2M = $2.098B (reconciles exactly; fees 0.49% of
  AUM); DIVISION D01 reconciles at 24-advisor scope. Screenshot dashboard_aum_waterfall.png. tsc PASS.

### ITEM 4 — export dashboard to PDF/PPT — DONE
- app/export/dashboard_export.py (reportlab PDF + python-pptx PPTX) renders the real
  ScopeDashboardService + AumNetFlowsService payloads (KPIs, net-flows bridge, top/bottom
  advisors). GET /export/dashboard?format=pdf|pptx; exec dashboard PDF/PPT buttons (downloadFile).
- Evidence: valid PDF v1.4 2-page (real $35.89M rev / $2.09B AUM extracted), valid PPTX;
  Playwright click-PDF real browser download (iperform_firm_f001_ytd.pdf). Screenshot export_buttons.png.

### ITEM 2 — 13B.3 division-leader guided journey — DONE
- 9-step DIVISION_STEPS in the existing story engine (no new backend): detect underperforming
  division → cross-advisor AI insight (persona=DDW) → drill worst real contributor → assign real
  coaching task → generate + accept/complete rec → division rollup moves by exactly the impact →
  division-scope AI closure. Launcher pre-resolves the division's own worst contributor.
- Evidence: real spine reconciles — D01 $14,738,198 → $14,785,251 = +$47,053.23 (= rec impact);
  3 coaching tasks persisted; AI insight 5 real drivers conf 0.82. Browser: persona DDW, Eastern
  Division, overlay Step 1/9, green proof bar names real lagging advisors. story_div_step1.png.

### ITEM 6 — AI-Assistant completion narration — DONE (real Claude)
- Strengthened context_assembler: completed actions ALWAYS narrate measured impact + explicit
  plain-language completion summary the LLM echoes.
- Evidence (real Claude): A012 BEFORE "no record of a recently completed initiative"; AFTER a
  "What Was Completed / Measured Financial Impact" section + LTM revenue $454K→$685K (= +$231,400
  impact). Transcript docs/qa_screenshots/session11/item6_narration_before_after.txt.

### SESSION 11 CLOSE — all 6 deferred items DONE
Final: backend 46 top-level routes + export/nbp/net-flows live (HTTP 200); frontend tsc PASS.
Commits: e77fd3c(item5+item1 labels) · 29ee2fa(item3) · cb0834e(item4) · 7e80d63(item2) ·
aae4b30(item6). Real Claude available all session (LLM_CLIENT_MODE=claude).

## Session 12 — 2026-07-07 — 4-item run (architecture audit + persona/UX fixes)
Real Claude available (LLM_CLIENT_MODE=claude). Commit per item.

### ITEM 1 — TigerGraph-vs-SQLite state audit → DATABASES.md (investigate only, NO code change)
- New DATABASES.md. Verdict: genuine architectural divergence (not a config-swap fallback).
  All durable state (bandit/learning weights, rec status, impact ledger, 6 memory types) is in
  SQLite via hardcoded SQLiteManager()/raw sqlite3 — no persistence adapter (BaseRepository is an
  empty stub). GraphClient IS a real adapter but the graph writes are best-effort ephemeral
  mirrors (mock store in-memory; replay_on_boot rehydrates the ledger). TG schema HAS most types
  (conversation_turn, reasoning_trace, context_memory w/ memory_type, feedback/outcome/learning +
  edges, all seeded) but LACKS impact_ledger + rec_status_transition vertices; procedural memory
  unpopulated; learning weight is not a vertex. Documented both SQLite DBs (iperform_features.db =
  active/settings path; iperform.db = preloaded snapshot), confirmed both DBs + Chroma gitignored
  + auto-recreated (CREATE-IF-NOT-EXISTS + reseed scripts; Chroma via ingest_sample_knowledge).
  Includes a concrete 6-step path (StateStore adapter + refactor ~6 call sites + 2 impls + 3
  schema additions). No code changed — for joint decision.

### ITEM 2 — DDW ≠ MDW; fix DDW text + build MDW market journey — DONE
- DDW (Division Director) and MDW (Market Director) are distinct. Division journey relabelled
  "Division-Leader Journey (DDW)", "DDW/MDW" text → "DDW".
- Built MARKET_STEPS (MDW, market scope). Real spine reconciles: Market M01 (Boston Metro)
  $3,713,409 → $3,760,462 = +$47,053.23; 3 tasks persisted; 5 real AI drivers. Browser: MDW
  persona, breadcrumb Market: Boston Metro, Step 1/9, green proof bar. mdw_step1.png.

### ITEM 3 — ID + Name everywhere via shared helper — DONE
- GET /hierarchy/entity-names (466 names); formatEntity() + useEntityLabel() hook. Applied to exec
  dashboard header/evidence/AI-title/advisor tables, shared AdvisorSelector, Advisor 360,
  Predictions. Header now "F001 · Chase Wealth Management Overview". item3_id_name_dashboard.png.

### ITEM 4 — consistent header hierarchy via shared tokens — DONE
- Canonical type.eyebrow < pageSubtitle < pageTitle(22px) tokens + shared PageHeader component.
  Applied to exec dashboard; swept 15 workspaces' ad-hoc text-[22px] font-black → type.pageTitle.
  item4_header_hierarchy.png. tsc PASS throughout.

Commits: 002a13f(item1) · efaf11d(item2) · f8137f4(item3) · 736bc61(item4).

## Session 13 — 2026-07-07 — TigerGraph as source of truth for durable state (large refactor)
Building the StateRepository adapter (graph primary + SQLite fallback) per DATABASES.md. Commit
per logical step; real Claude for AI-behavior checks. This is multi-step; status tracked here.

### STEP 1 — StateRepository adapter foundation + MEMORY domain end-to-end — DONE
- `app/repositories/state_repository.py`: StateRepository Protocol + SqliteStateRepository
  (delegates to existing SQLite logic, retained as fallback) + TigerGraphStateRepository (writes
  via TigerGraphMemoryLinker → graph vertices/edges; reads via graph TRAVERSAL) +
  FallbackStateRepository (primary→fallback, logged, never crashes) + get_state_repository().
  Config STATE_STORE_MODE=tigergraph(default)|sqlite. Filled the empty BaseRepository stub.
- New GQ mock query `get_context_memory_by_scope` (app/graph/queries/context_memory.py): reads an
  entity's context-memory by traversing phx_dm_memory_for_<scope> edges — the graph-native read
  replacing the SQLite SELECT.
- Repointed MemoryService through the adapter (no direct MemoryRepository/SQLite in the service).
- VERIFIED (real, mock graph): wrote a conversation turn → it landed as a phx_dm_context_memory
  GRAPH VERTEX (mem_...d2f988e3) + memory_for_advisor edge → retrieved via graph traversal through
  the adapter. Fallback proven: broke the graph primary → 5 memories returned from SQLite, NO
  crash, logged with full trace. STATE_STORE_MODE=sqlite legacy mode still works. Backend imports.
- REMAINING (next steps): repoint feedback/learning weights, impact ledger, recommendation status
  onto the adapter (currently still SQLite-direct); add impact_ledger + rec_status_transition
  vertex/edge schema; populate procedural memory organically; export current SQLite state → CSV +
  manifest so a graph-from-CSV rebuild reproduces history.
