# Part 15.4 — TigerGraph MCP-First Tool Runtime & Graph Persistence

## Added

- TigerGraph MCP-first graph runtime
- Dynamic TigerGraph MCP library adapter
- TigerGraph REST fallback adapter
- Mock graph store final fallback
- GraphRuntime facade
- Graph runtime status API
- Graph query API
- Vertex upsert API
- Edge upsert API
- Recommendation feedback persistence API
- Orchestration ToolRuntime patched to use GraphRuntime
- FeedbackLearningAgent patched to persist through GraphRuntime
- Graph Runtime UI page

## Runtime order

```text
GraphRuntime
  1. TigerGraph MCP
  2. TigerGraph REST
  3. MockGraphStore
```

## APIs

```text
GET  /graph-runtime/status
POST /graph-runtime/query
POST /graph-runtime/vertex
POST /graph-runtime/edge
POST /graph-runtime/feedback
```

## Environment

```text
GRAPH_ACCESS_STRATEGY=mcp_first
GRAPH_FALLBACK_ORDER=mcp,rest,mock

TIGERGRAPH_MCP_ENABLED=false
TIGERGRAPH_MCP_SERVER_URL=
TIGERGRAPH_MCP_TRANSPORT=http

TIGERGRAPH_REST_ENABLED=false
TIGERGRAPH_HOST=
TIGERGRAPH_GRAPH=iperform_insights_coaching_demo
```

## Important

The MCP adapter is intentionally dynamic because organization-specific TigerGraph MCP libraries may expose different client classes/methods. The app remains runnable without the library installed.

When your org MCP package is available, set:

```text
TIGERGRAPH_MCP_ENABLED=true
TIGERGRAPH_MCP_SERVER_URL=<your server>
```

## Next step

Part 15.5 — Chroma & Knowledge Services: real document ingestion, chunking, embedding creation, persistent Chroma collections, and retrieval APIs.
