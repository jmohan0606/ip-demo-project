# Last-Mile Integration Audit

This document lists areas that must be validated against real services before calling the package production-complete.

## Corrected now

### TigerGraph MCP
Status: corrected

- Uses official MCP stdio pattern.
- Uses `mcp.ClientSession`.
- Discovers tools with `session.list_tools()`.
- Calls tools using `session.call_tool("tigergraph__...")`.
- Executes installed app GSQL queries through `tigergraph__run_installed_query`.

### TigerGraph RESTPP
Status: corrected

- RESTPP base URL handling corrected.
- Installed query endpoint corrected.
- Graph upsert endpoint corrected.
- API token/JWT support added.
- Ping/smoke test added.

## Still needs real-environment validation

### 1. GSQL syntax on TigerGraph 4.2.2
Risk: medium/high  
Reason: GSQL syntax can be strict by version.  
Validation:

```bash
bash scripts/install_tigergraph_gsql_queries.sh
```

### 2. Installed query output shape
Risk: medium  
Reason: UI/backend may need transformation from TigerGraph raw result arrays.  
Validation:
Run each query and inspect response shape.

### 3. MCP tool argument schema
Risk: medium  
Reason: TigerGraph MCP versions may use slightly different argument names.  
Mitigation:
Tool mapper filters args based on discovered input schema.

### 4. RESTPP edge upsert with attributes
Risk: medium  
Reason: Edge payloads can vary if schema uses reverse edges, discriminators, or complex edge attributes.  
Validation:
Run `upsert_edge` on real graph.

### 5. pyTigerGraph existing-connection mode
Risk: medium  
Reason: Depends on tigergraph-mcp package version.  
Validation:

```bash
uv run python scripts/run_tigergraph_mcp_with_existing_connection.py
```

### 6. Azure OpenAI
Risk: low/medium  
Reason: Needs real endpoint, deployment name, API version.  
Validation:
`GET /llm-activation/status` should show `active_mode=azure_openai`.

### 7. Chroma
Risk: low/medium  
Reason: Current fallback works; production needs persistent deployment validation.  
Validation:
Ingest document, restart app, search document.

### 8. Frontend build
Risk: medium  
Reason: Requires actual `npm install` and `npm run build`.  
Validation:
Run frontend locally and capture real screenshots.

## Current honest status

The package is now corrected architecturally for TigerGraph MCP and RESTPP, but still requires real service validation before being called production-ready.
