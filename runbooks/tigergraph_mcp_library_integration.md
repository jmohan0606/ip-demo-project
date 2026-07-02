# TigerGraph MCP Library Integration Runbook

## 1. Install

```bash
uv sync
```

## 2. Configure Existing MCP Server

`.env`:

```text
ENABLE_TIGERGRAPH_MCP=true
TIGERGRAPH_MCP_USE_LIBRARY_CLIENT=true
TIGERGRAPH_MCP_CLIENT_MODE=streamable_http
TIGERGRAPH_MCP_URL=http://<your-mcp-server-host>:<port>/mcp
```

For SSE:

```text
TIGERGRAPH_MCP_CLIENT_MODE=sse
TIGERGRAPH_MCP_URL=http://<your-mcp-server-host>:<port>/sse
```

For stdio:

```text
TIGERGRAPH_MCP_CLIENT_MODE=stdio
TIGERGRAPH_MCP_STDIO_COMMAND=python
TIGERGRAPH_MCP_STDIO_ARGS=-m,tigergraph_mcp
```

## 3. Check MCP Tools

```bash
uv run python scripts/check_tigergraph_mcp_tools.py
```

## 4. Validate Graph Access

```bash
uv run python scripts/validate_graph_access.py
uv run python scripts/validate_tigergraph_mcp_library_integration.py
```

## 5. UI Check

```bash
uv run streamlit run app/ui/app_enterprise.py
```

Open:

```text
Graph Access Status -> MCP Tools
```

## 6. Required Tools

The application expects equivalent tool capabilities:

```text
health_check
query_graph
run_installed_query
upsert_vertex
upsert_edge
run_gsql
get_schema
```

Tool names can be mapped with:

```text
TIGERGRAPH_MCP_TOOL_HEALTH_CHECK
TIGERGRAPH_MCP_TOOL_QUERY_GRAPH
TIGERGRAPH_MCP_TOOL_RUN_INSTALLED_QUERY
TIGERGRAPH_MCP_TOOL_UPSERT_VERTEX
TIGERGRAPH_MCP_TOOL_UPSERT_EDGE
TIGERGRAPH_MCP_TOOL_RUN_GSQL
TIGERGRAPH_MCP_TOOL_GET_SCHEMA
```
