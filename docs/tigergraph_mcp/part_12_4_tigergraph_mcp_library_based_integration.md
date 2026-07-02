# Part 12.4 — TigerGraph MCP Library-Based Integration Package

## What Changed

Part 12.1 added an MCP-first graph access strategy, but it used a custom HTTP/JSON-RPC style wrapper.

Part 12.4 corrects this by adding an MCP SDK/library-based client:

```text
GraphAccessClient
  -> TigerGraphMcpClient
      -> TigerGraphMcpLibraryClient using MCP Python SDK
      -> legacy HTTP fallback only if needed
  -> TigerGraph REST fallback
  -> Local Mock fallback
```

## Dependencies Added

```text
mcp
tigergraph-mcp
pyTigerGraph
```

## Important Clarification

`tigergraph-mcp` is the TigerGraph MCP server package. The application should connect to an existing server using the MCP client SDK. This package supports:

- existing MCP server over Streamable HTTP
- existing MCP server over SSE
- stdio-launched MCP server command

## Settings

```text
TIGERGRAPH_MCP_USE_LIBRARY_CLIENT=true
TIGERGRAPH_MCP_CLIENT_MODE=streamable_http
TIGERGRAPH_MCP_URL=http://<host>:<port>/mcp
```

Supported modes:

```text
streamable_http
sse
stdio
```

For stdio:

```text
TIGERGRAPH_MCP_STDIO_COMMAND=python
TIGERGRAPH_MCP_STDIO_ARGS=-m,tigergraph_mcp
```

## Tool Discovery

```bash
uv run python scripts/check_tigergraph_mcp_tools.py
```

API:

```text
GET /graph-access/mcp-tools
```

UI:

```text
Graph Access Status -> MCP Tools
```

## Validate

```bash
uv run python scripts/validate_tigergraph_mcp_library_integration.py
```

## Graph Access Priority

```text
1. TigerGraph MCP library client
2. TigerGraph MCP legacy HTTP fallback
3. TigerGraph REST fallback
4. Local Mock Graph fallback
```
