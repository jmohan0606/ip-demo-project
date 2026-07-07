# Architecture Overview

Companion to `COPILOT_CONTEXT.md`. Covers the adapter interfaces, the end-to-end data flow, and
the module map. Authoritative build spec: `CLAUDE.md`. Data/persistence detail: `DATABASES.md`.

## 1. Adapter interfaces (Section 2 of the build spec)

Each adapter is a `Protocol` with concrete implementations selected by an env var via a cached
`get_*_client()` factory. Business code depends on the Protocol only.

```
GraphClient      app/graph/client.py
  .run_query(query_name, params) -> dict      # dispatches to @mock_query impls or real GSQL
  .upsert(entry, rows) / .health()
  implementations: MockGraphClient (FoundationGraphStore) · RealGraphClient (RESTPP) ·
                   TieredGraphClient (Tier1 MCP → Tier2 pyTigerGraph → Tier3 RESTPP → Tier4 mock)

LLMClient        app/llm/client.py
  .generate(prompt, context) -> str · .describe() -> dict
  MockLLMClient · ClaudeLLMClient (anthropic) · RealLLMClient (openai AzureOpenAI) ·
  AzureOpenAILLMClient (smart_sdk Model → _to_langgraph_model; key/fusion + certificate auth)

EmbeddingClient  app/llm/embedding_client.py
  .embed(text) / .embed_many(texts) -> list[float] · .describe()
  LocalEmbeddingClient (sentence-transformers, 384) · AzureOpenAIEmbeddingClient (smart_sdk) ·
  AzureOpenAIDirectEmbeddingClient (openai SDK)     # EMBEDDING_DIM must match the store DDL/Chroma

ModelClient      app/ml/client.py         (deterministic scorers | real XGBoost/GNN/forecast)
VectorClient     app/ml/vector_client.py  (local sqlite+cosine | tigergraph EMBEDDING/HNSW)
GuardrailClient  app/guardrails/client.py (local regex/heuristic | smartsdk EvaluationService)
```

**Adapter rules:** SDK imports live only inside the implementation class (guarded), so a missing
client-only package never blocks boot. Selection is centralized in the `get_*_client()` factory;
call sites never branch on mode.

## 2. End-to-end data flow (the agentic pipeline)

Real business data (hierarchy, revenue, AGP, CRM) flows through these stages, each persisting a
traceable artifact:

```
 raw facts (transactions, AUM/NCF, CRM, AGP)         seed: docs/tigergraph_foundation/data/
        │
        ▼  app/features/ + app/feature_store/
 Feature snapshots  ── lineage ─▶ which raw facts produced which feature value
        │            (phx_dm_feature_snapshot)
        ▼  app/embeddings/  (+ app/ml/gnn.py for GNN embeddings)
 Embeddings + Similarity  (phx_dm_embedding, phx_dm_similarity_match)
        │
        ▼  app/prediction/  (deterministic scorecard OR app/ml real XGBoost/GNN + SHAP)
 Predictions  ── contributions + confidence ─▶  (phx_dm_prediction_result)
        │
        ▼  app/opportunities/
 Opportunities  (severity/impact)  (phx_dm_opportunity)
        │
        ▼  app/recommendations/  (+ app/agents/nodes/compliance_agent.py compliance check)
 Recommendations  ── explainability chain ─▶  (phx_dm_recommendation)
        │            (features → prediction → opportunity → playbook → reasoning trace)
        ▼  app/feedback/   accept/complete/reject
 Feedback + Outcome  (phx_dm_feedback_event, phx_dm_outcome_event)
        │
        ▼  RL-style learning signal + outcome-driven learning (app/feedback, app/ml/fl_finetune.py)
 Learning signal  ── visibly reweights future recommendation ranking/confidence
        │            (phx_dm_learning_signal, bandit weights)
        └───────────────▶ closes the loop; next generation reflects what actually worked
```

**Stateful lifecycle (Section 13):** a recommendation moves `OPEN → ACCEPTED → IN_PROGRESS →
COMPLETED` (or `REJECTED`/`IGNORED`); completing one writes a real impact-ledger entry
(`phx_dm_impact_ledger`) linked back to the recommendation, and that change propagates to Advisor
360 / Revenue / Executive rollups and the AI Assistant's context.

**AI answer path** (`app/ai/chat/chat_engine.py`):
```
question
  → INPUT guardrails (PII redact, prompt-injection/jailbreak BLOCK)   app/guardrails/
  → context assembly (memory + RAG + insights + predictions/opps/recs + graph reasoning)
                                                                       app/ai/chat/context_assembler.py
  → graph relational reasoning (multi-hop traversal + prior-trace reuse)  app/ai/reasoning/graph_reasoner.py
  → LLM.generate (adapter)                                            app/llm/client.py
  → OUTPUT guardrails (PII filter, toxicity, grounding/hallucination) app/guardrails/
  → record reasoning trace (phx_dm_reasoning_trace + edges)          app/graph/artifacts.py
```

## 3. Reasoning-trace representation

One canonical vertex `phx_dm_reasoning_trace` (PK `reasoning_id`; `artifact_type`/`artifact_id`/
`created_at`) with edges `phx_dm_reasoning_uses_memory` and `phx_dm_reasoning_for_{advisor,
prediction,opportunity,recommendation}`. Used by BOTH the Explainability/Memory-Timeline display
and the reasoning-reuse path. Full detail in `DATABASES.md` → "Reasoning-trace consolidation".

## 4. Module map (backend `app/`)

| Module | Responsibility |
|--------|----------------|
| `api/` | FastAPI app (`main.py`) + routers (`routers/*.py`) |
| `config/` | Pydantic settings (all env vars) |
| `graph/` | GraphClient adapters, tiered client, foundation store, mock queries, artifact writes |
| `llm/` | LLMClient + EmbeddingClient adapters |
| `ml/` | ModelClient, VectorClient, GNN, forecast, training, SHAP, registry |
| `features/`, `feature_store/` | feature engineering + lineage |
| `embeddings/` | embedding generation + similarity |
| `prediction/` | prediction scoring (scorecard + real model promotion) |
| `opportunities/`, `recommendations/` | detection + ranking + lifecycle |
| `feedback/` | feedback events, outcomes, learning signal / bandit |
| `guardrails/` | input/output AI guardrails |
| `ai/` | chat engine, context assembler, reasoning, insights |
| `agents/` | agent registry, nodes (supervisor/compliance/coaching/rag), workflows (LangGraph) |
| `orchestration/` | agent orchestration runner |
| `memory/`, `services/memory_service.py` | 6 memory types (conversation/reasoning/semantic/…) |
| `knowledge/` | RAG: chunking, embedding provider, Chroma vector store, rag_service |
| `scope/`, `client360/`, `peers/` | persona/hierarchy rollups, 360 views, benchmarking |
| `agp/`, `crm/`, `revenue/`, `coaching/`, `whatif/` | domain modules |
| `impact` (in recommendations/feedback) | impact ledger + cross-screen propagation |
| `observability/` | LLM call/token/cost + stage-latency recorder |
| `ingestion/` | manifest-driven CSV ingestion + TigerGraph upsert |
| `repositories/` | state repository (TigerGraph source-of-truth + SQLite fallback) |
| `shared/` | ids, logging, responses, adapter logging |
| `models/` | Pydantic models |

## 5. Frontend map (`frontend/`)

- `app/(dashboard)/<page>/page.tsx` → thin page that renders `components/<area>/*-workspace.tsx`.
- `lib/navigation.ts` — sidebar nav (groups: Executive, Advisor, AI, Graph, Operations, Admin).
- `lib/api/client.ts` — `apiClient` (SSR uses internal loopback; browser uses
  `NEXT_PUBLIC_API_BASE_URL`). `lib/api/*.ts` — per-area typed helpers.
- `styles/tokens.ts` — colors/type/severity tokens. `components/ui/` — ShadCN primitives.
  `components/patterns/` + `components/cards/` — reusable KPI/AI-content/severity cards.
- Shared scope context (`components/layout/shell-context`) drives persona/hierarchy/period; pages
  consume it via a `useScopedAdvisor`-style hook so data re-fetches when scope changes.
