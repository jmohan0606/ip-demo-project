# iPerform Insights & Coaching

Enterprise local demo package for advisor insights, coaching, recommendations, feedback learning, context memory, and AI assistant chat.

## What This Builds

This project demonstrates a production-style wealth-management advisor coaching platform using local-machine technologies and optional TigerGraph connectivity.

Core capabilities:

- Streamlit enterprise UI
- FastAPI backend
- TigerGraph schema and GSQL package
- Enterprise wealth-management demo data
- Document ingestion and Chroma RAG
- Context Graph and Temporal Memory
- SQLite feature store
- Graph embeddings and similarity
- scikit-learn prediction engine
- Opportunity engine
- Recommendation engine
- Feedback learning loop
- AI Insights & Coaching engine
- AI Assistant Chat
- End-to-end demo orchestration

## Technology Stack

Local runtime:

- Python
- UV package manager
- FastAPI
- Streamlit
- SQLite
- Chroma
- NetworkX
- scikit-learn
- OpenAI adapter with mock fallback

External optional:

- TigerGraph 4.2.2 on AWS
- TigerGraph MCP server
- TigerGraph REST fallback
- OpenAI-compatible LLM adapter

## Graph Naming

```text
Graph:  iperform_insights_coaching_demo
Prefix: phx_dm_
```

## Quick Start

```bash
uv sync
uv run python scripts/final_smoke_test.py
uv run python run_local_api.py
uv run streamlit run app/ui/app_enterprise.py
```

API docs:

```text
http://127.0.0.1:8000/docs
```

## Recommended Demo Flow

1. Open Streamlit.
2. Go to **End-to-End Demo Run**.
3. Click **Run Full Demo Pipeline**.
4. Go to **Executive Dashboard**.
5. Click **Generate Dashboard Insights**.
6. Review insight cards and explainability.
7. Go to **Advisor 360**.
8. Go to **Recommendations**.
9. Submit feedback in **Feedback Learning**.
10. Ask questions in **AI Assistant Chat**.

## Important Scripts

```bash
uv run python scripts/final_smoke_test.py
uv run python scripts/run_full_demo.py
uv run python scripts/validate_final_demo.py
uv run python scripts/print_route_inventory.py
```

## Runbooks

```text
runbooks/quick_start.md
runbooks/local_demo_runbook.md
runbooks/tigergraph_setup_guide.md
runbooks/demo_story_script.md
```

## Package Notes

This package is local-runnable. Deployment files are intentionally not included.

TigerGraph can be connected later using MCP or REST configuration. If not configured, local mock fallback allows the demo to run end-to-end.


## Part 12.1 TigerGraph MCP-First Graph Access

Graph operations now route through:

```text
TigerGraph MCP Server -> TigerGraph REST fallback -> Local Mock Graph fallback
```

Validate:

```bash
uv run python scripts/validate_graph_access.py
```

UI page:

```text
Graph Access Status
```

API:

```text
GET /graph-access/health
```


## Part 12.2 Installation & Operations Guide

Complete handoff documentation has been added.

Start here:

```text
docs/README_OPERATIONS_INDEX.md
runbooks/quick_start.md
docs/setup/01_fresh_machine_install.md
```

Validate installation readiness:

```bash
uv run python scripts/check_installation_readiness.py
```

Full smoke test:

```bash
uv run python scripts/final_smoke_test.py
```


## Part 12.3 True Agentic Architecture

Adds LangGraph/LangChain-ready multi-agent architecture:

- Supervisor Agent
- Context Retrieval Agent
- TigerGraph Graph Agent
- RAG Knowledge Agent
- Prediction Agent
- Opportunity Agent
- Recommendation Agent
- Feedback Learning Agent
- Explainability Agent
- AI Assistant Agent

Validate:

```bash
uv run python scripts/validate_agentic_architecture.py
```

UI:

```text
Agentic AI Console
```


## Part 12.4 TigerGraph MCP Library-Based Integration

Replaces the custom MCP-first approach with a library-based MCP client using the Python MCP SDK, while keeping REST and mock fallback.

Validate:

```bash
uv run python scripts/validate_tigergraph_mcp_library_integration.py
uv run python scripts/check_tigergraph_mcp_tools.py
```

Docs:

```text
docs/tigergraph_mcp/part_12_4_tigergraph_mcp_library_based_integration.md
runbooks/tigergraph_mcp_library_integration.md
```


## Part 12.5 Preloaded Demo Databases

The package now ships with physical preloaded demo stores:

```text
data/sqlite/iperform.db
data/chroma/
```

Validate:

```bash
uv run python scripts/validate_preloaded_demo_databases.py
```


## Part 12.6 Final Audit, Gap Closure & Production-Ready Validation

Final validation and audit package.

Run:

```bash
uv run python scripts/run_final_audit.py
uv run python scripts/client_ready_validation.py
```

UI:

```text
Final Audit & Gap Closure
```

Reports:

```text
docs/final_audit/final_audit_report.json
docs/final_audit/requirement_traceability_audit.json
docs/final_audit/client_ready_validation_report.json
```


## Part 12.7 Final Runtime Validation & Bug-Fix Package

Runs real app-level runtime validation.

```bash
uv run python scripts/run_runtime_validation.py
uv run python scripts/client_demo_go_no_go.py
```

UI:

```text
Final Runtime Validation
```

API:

```text
GET /runtime-validation/run
```


## Part 12.8 Deep Runtime Hardening & Full Scenario Coverage

Closes previously partial items:

```bash
uv run python scripts/run_deep_hardening.py
uv run python scripts/final_no_partial_coverage_validation.py
```

UI:

```text
Deep Runtime Hardening
```


## Part 13.1 UI Architecture & Design System

Adds the new enterprise React/Next.js UI foundation under:

```text
frontend/
```

Run backend:

```bash
uv run python run_local_api.py
```

Run frontend:

```bash
cd frontend
npm install
npm run validate:ui
npm run dev
```

Open:

```text
http://localhost:3000
```


## Part 13.2 Navigation Shell & Persona Control

Adds React shell context, persona/scope/period/compare controls, active context bar, and enhanced navigation.

```bash
cd frontend
npm run validate:ui
npm run validate:navigation
npm run dev
```


## Part 13.3 Executive Dashboard

Adds the React Executive Dashboard page.

```bash
cd frontend
npm run validate:dashboard
npm run dev
```


## Part 13.5 Advisor 360 / Client 360

Adds advisor/client-level workspace.

```bash
cd frontend
npm run validate:advisor360
npm run dev
```


## Part 13.7 What-If Scenario Simulator

Adds scenario simulation and impact comparison.

```bash
cd frontend
npm run validate:whatif
npm run dev
```


## Part 13.10 AI Assistant Workspace

Adds dedicated enterprise AI Assistant chat page.

```bash
cd frontend
npm run validate:ai
npm run dev
```


## Part 13.12 Knowledge Graph Explorer

Adds React Flow based graph exploration workspace.

```bash
cd frontend
npm run validate:graph
npm run dev
```


## Part 13.14 Prediction & Forecasting

Adds the React prediction and forecasting workspace.

```bash
cd frontend
npm run validate:predictions
npm run dev
```


## Part 13.15 Memory Timeline & Explainability

Adds the React memory, reasoning, trace and explainability workspace.

```bash
cd frontend
npm run validate:memory
npm run dev
```


## Part 13.16 System Observability & Agent Operations

Adds enterprise runtime, agent and governance operations workspace.

```bash
cd frontend
npm run validate:observability
npm run dev
```

Next step: Part 13.17 — Final Enterprise UI Consolidation & Navigation Integration.


## Part 13.17 Final Enterprise UI Consolidation & Navigation Integration

Consolidates the React UI navigation and validates all enterprise routes.

```bash
cd frontend
npm run validate:final-ui
npm run validate:all-ui
npm run dev
```

Next step: Part 13.18 — Final UI Runtime Build Validation & Screenshot Review.


## Part 13.18 Final UI Runtime Build Validation & Screenshot Review

Adds final runtime route validation and optional Playwright screenshot capture.

```bash
cd frontend
npm install
npm run validate:runtime
npm run validate:screenshot-checklist
npm run build
npm run dev
```

Optional screenshots:

```bash
npx playwright install chromium
npm run screenshots
```

Next step: Run the app locally, capture screenshots, and review page-by-page against the approved mockups.


## Project Cleanup & Environment Configuration

Added project cleanup, env templates, runtime config module, config status API, and frontend config client.

```bash
cp .env.example .env
cp frontend/.env.local.example frontend/.env.local
uv run python scripts/validate_project_cleanup.py
```

For org Artifactory:

```bash
cp uv.toml.example uv.toml
cp frontend/.npmrc.example frontend/.npmrc
```


## Part 15.1 Persona-Aware Pixel-Perfect UI + End-to-End Backend/Agent Integration Foundation

Adds compact mockup-aligned dashboard styling, filter-driven backend calls, integrated FastAPI endpoints, What-If API, document ingestion to Chroma workflow, and TigerGraph coverage audit.

```bash
uv run python scripts/validate_part_15_1.py
uv run python run_local_api.py
cd frontend
npm run dev
```


## Part 15.2 API-Connected Pages Beyond Dashboard

Adds backend-connected Advisor 360, Recommendations, Graph Explorer, Feature Store/Embeddings, Memory/Explainability, and Knowledge/Chroma Search pages.

```bash
uv run python scripts/validate_part_15_2.py
uv run python run_local_api.py
cd frontend
npm run dev
```

Next step: Part 15.3 — Full End-to-End Backend Orchestration.


## Part 15.3 Full End-to-End Backend Orchestration

Adds supervisor/specialist agent orchestration, tool runtime, evidence, trace, and `/orchestration/run`.

```bash
uv run python scripts/validate_part_15_3.py
uv run python run_local_api.py
cd frontend
npm run dev
```

Open:

```text
http://localhost:3000/orchestration
```

Next step: Part 15.4 — TigerGraph MCP-First Tool Runtime & Graph Persistence.


## Part 15.4 TigerGraph MCP-First Tool Runtime & Graph Persistence

Adds MCP-first graph runtime with REST and mock fallback, graph persistence APIs, orchestration tool integration, and UI page.

```bash
uv run python scripts/validate_part_15_4.py
uv run python run_local_api.py
cd frontend
npm run dev
```

Open:

```text
http://localhost:3000/graph-runtime
```

Next step: Part 15.5 — Chroma & Knowledge Services.


## Part 15.5 Chroma & Knowledge Services

Adds real knowledge runtime, document chunking, Chroma persistent collection support, JSON vector-store fallback, retrieval APIs, upload API, graph document lineage, and UI page.

```bash
uv run python scripts/validate_part_15_5.py
uv run python run_local_api.py
cd frontend
npm run dev
```

Open:

```text
http://localhost:3000/knowledge-runtime
```

Next step: Part 15.6 — Feature Store & Prediction Platform.


## Part 15.6 Feature Store & Prediction Platform

Adds SQLite feature store, feature engineering, similarity search, prediction runtime, graph persistence, and feature runtime UI.

```bash
uv run python scripts/validate_part_15_6.py
uv run python run_local_api.py
cd frontend
npm run dev
```

Open:

```text
http://localhost:3000/feature-runtime
```

Next step: Part 15.7 — Recommendation & Learning Engine.


## Part 15.7 Recommendation & Learning Engine

Adds opportunity generation, recommendation ranking, compliance checks, knowledge evidence, feedback learning, memory updates, graph persistence, and UI runtime page.

```bash
uv run python scripts/validate_part_15_7.py
uv run python run_local_api.py
cd frontend
npm run dev
```

Open:

```text
http://localhost:3000/recommendation-runtime
```

Next step: Part 15.8 — Memory & Context Platform.


## Part 15.8 Memory & Context Platform

Adds SQLite memory store, context engineering, memory retrieval, pruning, compression, context packets, graph persistence, and UI runtime page.

```bash
uv run python scripts/validate_part_15_8.py
uv run python run_local_api.py
cd frontend
npm run dev
```

Open:

```text
http://localhost:3000/memory-runtime
```

Next step: Part 15.9 — Production Readiness & Security.


## Part 16.1 Real TigerGraph MCP Integration & Production Data Activation

Adds production TigerGraph MCP activation runtime, logical query contracts, activation APIs, smoke tests, and UI page.

```bash
uv run python scripts/validate_part_16_1.py
uv run python scripts/tigergraph_activation_smoke_test.py
uv run python run_local_api.py
cd frontend
npm run dev
```

Open:

```text
http://localhost:3000/tigergraph-activation
```

Next step: Part 16.2 — Production Data Load, Schema Verification & GSQL Query Installation.


## Part 16.2 Production Data Load, Schema Verification & GSQL Query Installation

Adds TigerGraph production schema, loading job, analytical query contracts, GSQL installation scripts and schema verification.

```bash
uv run python scripts/validate_part_16_2.py
uv run python scripts/verify_tigergraph_schema_contracts.py
bash scripts/install_tigergraph_gsql_queries.sh
```

Next step: Part 16.3 — Real Azure OpenAI / LLM Agent Activation.


## Part 16.3 Real Azure OpenAI / LLM Agent Activation

Adds Azure OpenAI runtime, fallback LLM, grounded AI Assistant, recommendation narratives, memory writeback and LLM activation UI.

```bash
uv run python scripts/validate_part_16_3.py
uv run python run_local_api.py
cd frontend
npm run dev
```

Open:

```text
http://localhost:3000/llm-activation
```

Next step: Part 16.4 — Final Runtime Build Fixes + Real Browser Screenshot Validation.


## Part 16.4 Final Runtime Build Fixes + Real Browser Screenshot Validation

Adds runtime preflight, API health check, real browser screenshot automation and final validation runners.

```bash
bash scripts/final_runtime_validation.sh
uv run python run_local_api.py
uv run python scripts/final_api_health_check.py
cd frontend && npm run dev
cd ..
uv run python scripts/capture_browser_screenshots.py
```

Next step: Part 16.5 — Final Consolidated Working Package.


## Part 16.5 Final Consolidated Working Package

This is the final consolidated package.

Start here:

```bash
cat START_HERE.md
uv run python scripts/final_release_check.py
uv run python scripts/runtime_preflight.py
uv run python run_local_api.py
```

Then:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:3000/dashboard
```

Release status:

```text
RC-2 Ready for Local Run and Enterprise Integration Testing
```


## TigerGraph MCP Corrected Source of Truth

The TigerGraph layer has been corrected to follow the official tigergraph-mcp pattern:

- stdio MCP server
- `mcp.ClientSession`
- dynamic `session.list_tools()`
- official `session.call_tool("tigergraph__...")`
- official TG_* env variables
- installed app GSQL queries executed via `tigergraph__run_installed_query`

Read:

```text
docs/TIGERGRAPH_MCP_CORRECTED_SOURCE_OF_TRUTH.md
```

Validate static correction:

```bash
uv run python scripts/validate_tigergraph_corrected_source_of_truth.py
```

Validate real MCP runtime:

```bash
uv run python scripts/tigergraph_mcp_discover_tools.py
uv run python scripts/tigergraph_mcp_official_smoke_test.py
```


## TigerGraph RESTPP Corrected Audit

RESTPP fallback has been corrected and documented.

Read:

```text
docs/TIGERGRAPH_RESTPP_CORRECTED_AUDIT.md
docs/LAST_MILE_INTEGRATION_AUDIT.md
```

Validate:

```bash
uv run python scripts/validate_tigergraph_restpp_corrected.py
uv run python scripts/tigergraph_restpp_smoke_test.py
```


## Part 17 Emergency UI Remediation

Run:
```bash
uv run python scripts/validate_part17_emergency_ui.py
uv run python run_local_api.py
cd frontend
npm install lucide-react recharts
npm run dev
```


## Part 17.5 Enterprise UI + TigerGraph Consolidated Package

Use this package now. It includes UI remediation, corrected TigerGraph source of truth, MCP/RESTPP contracts, and RESTPP sample data loader.
