# Local Demo Runbook

## 1. Install

```bash
uv sync
```

## 2. Validate package

```bash
uv run python scripts/validate_final_demo.py
```

## 3. Run API

```bash
uv run python run_local_api.py
```

Open:

```text
http://127.0.0.1:8000/docs
```

## 4. Run Enterprise Streamlit UI

```bash
uv run streamlit run app/ui/app_enterprise.py
```

## 5. Recommended Demo Flow

1. Open **End-to-End Demo Run**
2. Click **Run Full Demo Pipeline**
3. Go to **Executive Dashboard**
4. Click **Generate Dashboard Insights**
5. Go to **Advisor 360**
6. Go to **Recommendations**
7. Accept/reject a recommendation in **Feedback Learning**
8. Ask a question in **AI Assistant Chat**

## 6. TigerGraph

This local demo can run without TigerGraph connectivity using local mock fallback.

When TigerGraph MCP/REST is available, set `.env` values:

```text
ENABLE_TIGERGRAPH_MCP=true
TIGERGRAPH_MCP_URL=...
ENABLE_TIGERGRAPH_REST_FALLBACK=true
TIGERGRAPH_HOST=...
TIGERGRAPH_GRAPH=iperform_insights_coaching_demo
TIGERGRAPH_SCHEMA_PREFIX=phx_dm_
```
