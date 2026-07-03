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

Completed: 0B audit; Phase 1 foundation (verified: app boots, adapters live, store loads 109,328 rows).
In progress: Phase 2 — local TigerGraph Docker attempt.
Known issues / deferred: `/recommendations` engine broken (rebuild Phase 8); `/ui-integrated/*`
still present until Phase 10/11 page rebuilds; frontend still calls losing-family endpoints
until rebuild; old `tigergraph/sample_data` (51 CSVs) still feeds `app/feature_store` until
Phase 3/5 repoints it at the foundation data; services not yet consuming GraphClient/LLMClient
(Phase 3+ wires them).
Next: 1) Phase 2 — local TigerGraph Docker; 2) Phase 3 — GQ-### mock+real call sites;
3) Phase 4 — AGP/CRM modules.
