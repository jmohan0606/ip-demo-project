# Environment Configuration

## Minimum Local Demo Configuration

Use this when you want the demo to run without external TigerGraph or OpenAI.

```text
ENABLE_LOCAL_MOCK_FALLBACK=true
ENABLE_TIGERGRAPH_MCP=false
ENABLE_TIGERGRAPH_REST_FALLBACK=false
MODEL_PROVIDER=mock
```

## TigerGraph MCP-First Configuration

```text
GRAPH_ACCESS_STRATEGY=mcp_rest_mock
ENABLE_TIGERGRAPH_MCP=true
TIGERGRAPH_MCP_URL=http://<your-mcp-host>:<port>/mcp
TIGERGRAPH_MCP_API_KEY=
TIGERGRAPH_MCP_AUTH_HEADER=Authorization
TIGERGRAPH_MCP_AUTH_SCHEME=Bearer
TIGERGRAPH_GRAPH=iperform_insights_coaching_demo
TIGERGRAPH_SCHEMA_PREFIX=phx_dm_
```

## REST Fallback

```text
ENABLE_TIGERGRAPH_REST_FALLBACK=true
TIGERGRAPH_HOST=https://<your-tigergraph-host>
TIGERGRAPH_USERNAME=<optional>
TIGERGRAPH_PASSWORD=<optional>
TIGERGRAPH_SECRET=<optional>
```

## OpenAI Adapter

```text
MODEL_PROVIDER=openai
OPENAI_API_KEY=<your-key>
OPENAI_MODEL=gpt-4o-mini
```

If no model key is configured, mock fallback still allows the demo to run.
