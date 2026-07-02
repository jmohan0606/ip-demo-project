# Configuration Cleanup

This package removes the confusing duplicate TigerGraph configuration.

## Kept settings

Only these TigerGraph settings should be used:

```text
TG_GRAPHNAME
TIGERGRAPH_GRAPH
TG_HOST
TG_USERNAME
TG_PASSWORD
TG_API_TOKEN
TG_JWT_TOKEN
TG_RESTPP_PORT
TG_GS_PORT
TG_TGCLOUD
TG_PROFILE
TIGERGRAPH_MCP_ENABLED
TIGERGRAPH_MCP_COMMAND
TIGERGRAPH_MCP_ARGS
TIGERGRAPH_REST_ENABLED
TIGERGRAPH_RESTPP_URL
TIGERGRAPH_REST_QUERY_METHOD
```

## Removed / avoid

Avoid using older/generated names that point to non-prefixed graph assets or the root `gsql/` folder.

## Required runtime order

```text
TigerGraph MCP official stdio
  -> TigerGraph RESTPP fallback
  -> Mock fallback
```
