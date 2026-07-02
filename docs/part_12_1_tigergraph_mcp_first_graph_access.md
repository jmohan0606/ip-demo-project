# Part 12.1 — TigerGraph MCP-First Graph Access Package

## What Changed

The application now uses a centralized graph access layer with this priority:

```text
1. Existing TigerGraph MCP Server
2. TigerGraph REST API fallback
3. Local Mock Graph Data Service final fallback
```

## Added

- `GraphAccessClient`
- `GraphAccessService`
- Real HTTP-capable `TigerGraphMcpClient`
- JSON-RPC MCP `tools/call` support
- Direct `/tools/{tool_name}` fallback support
- Mock graph service backed by enterprise demo CSVs
- Graph access API endpoints
- Streamlit Graph Access Status page
- Validation scripts
- Unit/integration tests

## API

```text
GET  /graph-access/health
POST /graph-access/health-check
GET  /graph-access/schema
POST /graph-access/query
POST /graph-access/installed-query
POST /graph-access/upsert-vertex
POST /graph-access/upsert-edge
```

## MCP Tool Names

Configured through `.env`:

```text
TIGERGRAPH_MCP_TOOL_HEALTH_CHECK=health_check
TIGERGRAPH_MCP_TOOL_QUERY_GRAPH=query_graph
TIGERGRAPH_MCP_TOOL_RUN_INSTALLED_QUERY=run_installed_query
TIGERGRAPH_MCP_TOOL_UPSERT_VERTEX=upsert_vertex
TIGERGRAPH_MCP_TOOL_UPSERT_EDGE=upsert_edge
TIGERGRAPH_MCP_TOOL_RUN_GSQL=run_gsql
TIGERGRAPH_MCP_TOOL_GET_SCHEMA=get_schema
```

## UI Upload Behavior

The existing ingestion/upload workflow already calls `TigerGraphUpsertClient`.
That compatibility wrapper now routes to `GraphAccessClient`, so UI uploads follow:

```text
UI Upload
  -> Ingestion Service
  -> TigerGraphUpsertClient
  -> GraphAccessClient
  -> MCP
  -> REST fallback
  -> Mock fallback
```

## Validate

```bash
uv run python scripts/validate_graph_access.py
```
