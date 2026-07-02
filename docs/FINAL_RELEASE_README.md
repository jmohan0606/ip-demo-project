# iPerform Insights & Coaching — Final Consolidated Working Package

## Release

**Release Candidate:** RC-2  
**Package:** Part 16.5 — Final Consolidated Working Package  
**Status:** Ready for local execution and enterprise integration testing

## What is included

### UI Workspaces
- Executive / Advisor Dashboard
- Revenue Analytics
- Advisor 360 / Client 360
- AGP Goals & Coaching
- What-If Simulator
- Opportunities & Recommendations
- Recommendation Impact / ROI
- AI Assistant
- Knowledge / Playbooks / Compliance
- Document Ingestion / Chroma Runtime
- Knowledge Graph Explorer
- TigerGraph Runtime
- TigerGraph Activation
- Feature Store / Embeddings / Similarity
- Feature Runtime
- Prediction & Forecasting
- Memory Timeline & Explainability
- Memory Runtime
- Agent Orchestration
- LLM Activation
- Observability / Agent Operations

### Backend Runtime Services
- FastAPI runtime
- Supervisor/specialist agent orchestration
- TigerGraph MCP-first runtime
- TigerGraph REST fallback
- Mock graph fallback
- Chroma persistent collection support
- JSON vector fallback
- SQLite feature store
- Prediction runtime
- Recommendation learning runtime
- Memory/context runtime
- Azure OpenAI runtime
- Mock LLM fallback

## Local run order

### 1. Backend

```bash
uv sync
uv run python scripts/runtime_preflight.py
uv run python run_local_api.py
```

Backend URL:

```text
http://127.0.0.1:8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend URL:

```text
http://localhost:3000/dashboard
```

### 3. Validation

```bash
uv run python scripts/final_api_health_check.py
bash scripts/final_runtime_validation.sh
```

### 4. Real screenshots

```bash
cd frontend
npx playwright install chromium
cd ..
uv run python scripts/capture_browser_screenshots.py
```

Screenshots will be created under:

```text
docs/real_browser_screenshots/
```

## Production integration env

```text
TIGERGRAPH_MCP_ENABLED=true
TIGERGRAPH_MCP_SERVER_URL=<your tigergraph mcp server>
TIGERGRAPH_REST_ENABLED=true
TIGERGRAPH_HOST=<your tigergraph host>
TIGERGRAPH_GRAPH=iPerformInsights

AZURE_OPENAI_ENABLED=true
AZURE_OPENAI_ENDPOINT=<your endpoint>
AZURE_OPENAI_API_KEY=<your key>
AZURE_OPENAI_DEPLOYMENT=<your deployment>

CHROMA_PERSIST_DIR=data/chroma
CHROMA_COLLECTION_NAME=iperform_knowledge_base
SQLITE_DB_PATH=data/sqlite/iperform.db
```

## Final note

The application runs locally in fallback mode even without TigerGraph MCP, Azure OpenAI, or chromadb.  
For production data activation, configure TigerGraph MCP/REST and Azure OpenAI.
