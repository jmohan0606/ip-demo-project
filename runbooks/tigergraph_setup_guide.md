# TigerGraph Setup Guide

## Graph

```text
iperform_insights_coaching_demo
```

## Prefix

```text
phx_dm_
```

## Recommended WebShell Order

```text
1. tigergraph/schema/01_vertices.gsql
2. tigergraph/schema/02_edges.gsql
3. tigergraph/schema/03_create_graph.gsql
4. tigergraph/queries_v1/*.gsql
```

## Application Connectivity

Set `.env`:

```text
TIGERGRAPH_GRAPH=iperform_insights_coaching_demo
TIGERGRAPH_SCHEMA_PREFIX=phx_dm_
ENABLE_TIGERGRAPH_MCP=true
TIGERGRAPH_MCP_URL=<your tigergraph mcp server>
ENABLE_TIGERGRAPH_REST_FALLBACK=true
TIGERGRAPH_HOST=<your tigergraph host>
TIGERGRAPH_USERNAME=<optional>
TIGERGRAPH_PASSWORD=<optional>
TIGERGRAPH_SECRET=<optional>
```

## Local Fallback

For local demo without TigerGraph:

```text
ENABLE_LOCAL_MOCK_FALLBACK=true
ENABLE_TIGERGRAPH_MCP=false
ENABLE_TIGERGRAPH_REST_FALLBACK=false
```
