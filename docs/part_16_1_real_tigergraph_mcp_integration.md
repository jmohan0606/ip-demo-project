# Part 16.1 — Real TigerGraph MCP Integration & Production Data Activation

## Added

- TigerGraph logical query contracts
- Production activation runtime
- MCP-first query mapping
- REST fallback query mapping
- Production activation smoke test
- TigerGraph activation APIs
- TigerGraph activation UI page
- GSQL/MCP contract documentation

## Runtime order

```text
Application logical query
  → TigerGraphProductionRuntime
  → Query contract
  → GraphRuntime
  → TigerGraph MCP
  → TigerGraph REST
  → Mock fallback
```

## APIs

```text
GET  /tigergraph-activation/status
POST /tigergraph-activation/query
POST /tigergraph-activation/smoke-test
```

## Required production activation env

```text
TIGERGRAPH_MCP_ENABLED=true
TIGERGRAPH_MCP_SERVER_URL=<your tigergraph mcp server>
TIGERGRAPH_MCP_TRANSPORT=http

TIGERGRAPH_REST_ENABLED=true
TIGERGRAPH_HOST=<your tigergraph host>
TIGERGRAPH_GRAPH=iperform_insights_coaching_demo
TIGERGRAPH_TOKEN=<token if used>
```

## Production cutover rule

Local validation can pass in mock mode.

Production cutover requires:

```text
production_data_activation=true
active_mode=mcp or rest
```

## Next step

Part 16.2 — Production Data Load, Schema Verification & GSQL Query Installation.
