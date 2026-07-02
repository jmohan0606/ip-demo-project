# Existing TigerGraph MCP Server Setup

## Required MCP Tools

Your existing MCP server should expose equivalent tools:

```text
health_check
query_graph
run_installed_query
upsert_vertex
upsert_edge
run_gsql
get_schema
```

Tool names can be overridden in `.env`:

```text
TIGERGRAPH_MCP_TOOL_HEALTH_CHECK=health_check
TIGERGRAPH_MCP_TOOL_QUERY_GRAPH=query_graph
TIGERGRAPH_MCP_TOOL_RUN_INSTALLED_QUERY=run_installed_query
TIGERGRAPH_MCP_TOOL_UPSERT_VERTEX=upsert_vertex
TIGERGRAPH_MCP_TOOL_UPSERT_EDGE=upsert_edge
TIGERGRAPH_MCP_TOOL_RUN_GSQL=run_gsql
TIGERGRAPH_MCP_TOOL_GET_SCHEMA=get_schema
```

## Validation

```bash
uv run python scripts/validate_graph_access.py
```

## UI Validation

Run Streamlit:

```bash
uv run streamlit run app/ui/app_enterprise.py
```

Open:

```text
Graph Access Status
```

Click:

```text
Check Active Graph Access Mode
```

Expected order:

```text
MCP -> REST -> Mock
```
