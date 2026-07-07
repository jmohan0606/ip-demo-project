# Copilot Context — iPerform Insights & Coaching

A condensed primer for GitHub Copilot (and any developer) working in this repo where Claude Code
isn't available. Read this first, then `ARCHITECTURE_OVERVIEW.md` for the module map and
`TROUBLESHOOTING.md` for real gotchas. The authoritative build spec is `CLAUDE.md`.

## What this app is

An enterprise **wealth-management advisor insights & coaching platform** demo. Its centerpiece is
an **agentic AI pipeline running on real, internally-consistent business data** (firm → division →
region → market → advisor hierarchy; revenue/AUM/NCF; CRM; AGP program):

> Feature Engineering → Embeddings/Similarity → Predictions (ML/GNN) → Opportunities →
> Recommendations → Feedback/Outcome → Learning signal (RL-style reward/rank update)

Everything an AI produces (prediction, recommendation, insight, similarity score) **persists a
traceable artifact** (which features/evidence produced it) — never just a number. Business logic is
**real code**, not hardcoded response dicts.

- **Backend:** Python 3.12, FastAPI (`app/api/main.py`), Pydantic v2 settings (`app/config/settings.py`).
- **Frontend:** Next.js 14 + TypeScript + Tailwind + ShadCN UI + Recharts + Framer Motion
  (`frontend/`). Dark navy sidebar + light canvas. Design tokens in `frontend/styles/tokens.ts`.
- **Data/graph:** TigerGraph schema + 192 manifest-controlled seed CSVs (60 vertex + 132 edge
  types, 156,247 rows) in `docs/tigergraph_foundation/` (the source-of-truth "foundation
  package" — see `TIGERGRAPH_AUDIT.md`; root `tigergraph/` is legacy/reference-only). At runtime
  in mock mode, an in-memory `FoundationGraphStore` loads those CSVs. The Data Ingestion & Sync
  page can load the ENTIRE dataset via "Run All Ingestion" (`POST /ingestion/run-all`).
- **No Streamlit, no MUI, no purple.** Every page is a distinct component from shared primitives.

## The adapter pattern (the single most important concept)

All external systems sit behind an **adapter interface**, selected by an env var. Service/business
code depends ONLY on the interface — never imports an SDK directly. This is why the same code runs
on the build box (mock/free) and the client machine (real JPMC systems) with only env changes.

| Concern | Interface (file) | Modes (env var) | Getter |
|---------|------------------|-----------------|--------|
| Graph | `app/graph/client.py` GraphClient | `GRAPH_CLIENT_MODE=mock\|local_real\|real\|auto\|tiered\|mcp` | `get_graph_client()` |
| LLM | `app/llm/client.py` LLMClient | `LLM_CLIENT_MODE=mock\|claude\|real\|azure` | `get_llm_client()` |
| Embedding | `app/llm/embedding_client.py` EmbeddingClient | `EMBEDDING_CLIENT_MODE=local\|azure\|azure_openai` | `get_embedding_client()` |
| ML model | `app/ml/client.py` ModelClient | `MODEL_CLIENT_MODE=deterministic\|real` | `get_model_client()` |
| Vector | `app/ml/vector_client.py` VectorClient | `VECTOR_CLIENT_MODE=local\|tigergraph` | `get_vector_client()` |
| Rerank | (see settings) | `RERANK_CLIENT_MODE=local\|cohere` | — |
| Guardrails | `app/guardrails/client.py` GuardrailClient | `GUARDRAIL_CLIENT_MODE=local\|smartsdk` | `get_guardrail_client()` |

**Rule:** SDK imports (`pyTigerGraph`, `openai`, `anthropic`, `smart_sdk`, `torch`, `xgboost`,
`sentence_transformers`) live ONLY inside their `Real*`/`Claude*`/`Azure*` adapter class, inside
`__init__` or the method — **never at module top level elsewhere**. A guarded import means the app
boots in every other mode even when a client-only package (e.g. `smart_sdk`) is absent.

## The five environment swaps (build box → client)

Nothing about business/prompt/query logic changes; only these selectors do (see
`CLIENT_ENV_SETUP.md` for full values):

| Selector | Build box | Client (JPMC) |
|----------|-----------|---------------|
| `GRAPH_CLIENT_MODE` | `mock` | `real` (live TigerGraph, getToken(secret), SSL) |
| `LLM_CLIENT_MODE` | `mock`/`claude` | `azure` (SmartSDK/Fusion) |
| `EMBEDDING_CLIENT_MODE` | `local` | `azure` (SmartSDK) |
| `MODEL_CLIENT_MODE` | `deterministic` | `real` |
| `VECTOR_CLIENT_MODE` | `local` | `local`/`tigergraph` |

`smart_sdk` (JPMC Azure/Fusion + LangGraph re-exports) is client-artifactory-only; see
`SMARTSDK_REFERENCE.md` for the confirmed code and `CLIENT_ENV_SETUP.md` for setup. Native
LangGraph construction is isolated in `app/agents/workflows/langgraph_builder.py` so the SmartSDK
swap is a one-file edit.

## Where things live (quick map)

- **AI request/response path:** `app/ai/chat/chat_engine.py` (assembles context, runs
  input/output guardrails, calls the LLM, records a reasoning trace).
- **Guardrails:** `app/guardrails/` (PII redaction, prompt-injection/jailbreak, toxicity,
  grounding). Endpoints `/guardrails/*`.
- **Pipeline stages:** `app/features/` (+`app/feature_store/`), `app/embeddings/`,
  `app/prediction/`, `app/opportunities/`, `app/recommendations/`, `app/feedback/`, `app/ml/`.
- **Graph:** `app/graph/` — `client.py` (mock + RESTPP real), `tiered_client.py` (4-tier
  MCP→pyTigerGraph→RESTPP→mock), `foundation_store.py` (in-memory seed loader), `queries/` (mock
  query impls registered via `@mock_query`), `artifacts.py` (writes AI-artifact vertices/edges).
- **Persona/scope rollups:** `app/scope/`, `app/client360/`, `app/peers/`.
- **Memory / reasoning:** `app/memory/`, `app/services/memory_service.py`,
  `app/ai/reasoning/graph_reasoner.py`. See `DATABASES.md` for the single reasoning-trace rep.
- **API routers:** `app/api/routers/*.py`, registered in `app/api/main.py`.
- **Frontend pages:** `frontend/app/(dashboard)/<page>/page.tsx` → renders a component in
  `frontend/components/<area>/`. Nav in `frontend/lib/navigation.ts`. API calls via
  `frontend/lib/api/client.ts` (`apiClient`).
- **Env health / setup verification:** `GET /env-health` + `frontend/.../env-health`.

## Conventions

- Every "done" claim in this project is backed by real evidence (real command output, real
  screenshots to `docs/qa_screenshots/`, real Claude for AI-behavior checks — never mock for that).
- Update `PROGRESS.md` (session log) and `STATUS_CHECK.md` (verification log) as you work.
- Secrets only in `.env` (gitignored); `.env.example` has placeholders. Never commit real keys.
- Run the backend: `uvicorn app.api.main:app --host 127.0.0.1 --port 8000`. Frontend:
  `cd frontend && npm run dev` (port 3000). Frontend typecheck: `cd frontend && npx tsc --noEmit`.
