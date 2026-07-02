# TigerGraph Setup

## Graph Name

```text
iperform_insights_coaching_demo
```

## Prefix

All vertices and edges use:

```text
phx_dm_
```

## WebShell Order

Run the schema files in this order:

```text
tigergraph/schema/01_vertices.gsql
tigergraph/schema/02_edges.gsql
tigergraph/schema/03_create_graph.gsql
```

Then install V1 queries:

```text
tigergraph/queries_v1/*.gsql
```

## Data Upload Options

The package supports:

1. UI upload from **Data Ingestion & Sync**
2. Code-based ingestion through `/ingestion/run`
3. MCP-first graph upsert through `/graph-access/upsert-vertex`
4. REST fallback if MCP is unavailable
5. Mock fallback if both MCP and REST are unavailable

## Validate Graph Access

```bash
uv run python scripts/validate_graph_access.py
```

The output will show active mode:

```text
mcp
rest
mock
```
