# TigerGraph MCP-First Access Runbook

## Goal

Connect this local demo package to your existing TigerGraph MCP server as the primary graph access path.

## Environment

```text
ENABLE_TIGERGRAPH_MCP=true
TIGERGRAPH_MCP_URL=http://<your-mcp-host>:<port>/mcp
TIGERGRAPH_MCP_API_KEY=<optional>
TIGERGRAPH_MCP_AUTH_HEADER=Authorization
TIGERGRAPH_MCP_AUTH_SCHEME=Bearer

ENABLE_TIGERGRAPH_REST_FALLBACK=true
TIGERGRAPH_HOST=https://<your-tigergraph-host>
TIGERGRAPH_GRAPH=iperform_insights_coaching_demo
TIGERGRAPH_SCHEMA_PREFIX=phx_dm_

ENABLE_LOCAL_MOCK_FALLBACK=true
```

## Required MCP Tools

Your existing TigerGraph MCP server should expose equivalent tools:

```text
health_check
query_graph
run_installed_query
upsert_vertex
upsert_edge
run_gsql
get_schema
```

Tool names can be changed in `.env`.

## Validate

```bash
uv run python scripts/validate_graph_access.py
```

## Check from API

```bash
uv run python run_local_api.py
```

Open:

```text
http://127.0.0.1:8000/docs
```

Then call:

```text
GET /graph-access/health
```

## Check from UI

```bash
uv run streamlit run app/ui/app_enterprise.py
```

Open:

```text
Graph Access Status
```
