# TigerGraph MCP Corrected Source of Truth

The TigerGraph layer has been corrected to follow the official TigerGraph MCP pattern.

## What was wrong before

The earlier generated code assumed a custom Python client with methods such as:

```python
client.execute_query(...)
client.upsert_vertex(...)
client.upsert_edge(...)
```

That is not how the official `tigergraph-mcp` README shows client usage.

## Correct pattern

TigerGraph MCP runs as an MCP server and exposes official tools named `tigergraph__...`.

The corrected implementation uses:

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command="tigergraph-mcp",
    args=["-vv"],
    env={
        "TG_HOST": "http://localhost",
        "TG_USERNAME": "tigergraph",
        "TG_PASSWORD": "tigergraph",
        "TG_GRAPHNAME": "iPerformInsights",
    },
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        result = await session.call_tool(
            "tigergraph__run_installed_query",
            arguments={
                "graph_name": "iPerformInsights",
                "query_name": "get_advisor_context",
                "params": {"advisor_id": "ADV0001"},
            },
        )
```

## Correct distinction

Application logical query names are not MCP tool names.

| App logical query | Installed GSQL query | MCP tool |
|---|---|---|
| advisor_context | get_advisor_context | tigergraph__run_installed_query |
| revenue_summary | get_revenue_summary | tigergraph__run_installed_query |
| advisor_360 | get_advisor_360 | tigergraph__run_installed_query |
| recommendation_context | get_recommendation_context | tigergraph__run_installed_query |
| memory_timeline | get_memory_timeline | tigergraph__run_installed_query |
| graph_explorer | get_graph_explorer | tigergraph__run_installed_query |

## Official tools used

- tigergraph__list_graphs
- tigergraph__get_graph_schema
- tigergraph__show_graph_details
- tigergraph__run_installed_query
- tigergraph__run_query
- tigergraph__gsql
- tigergraph__install_query
- tigergraph__is_query_installed
- tigergraph__add_node
- tigergraph__add_edge
- tigergraph__get_vertex_count
- tigergraph__get_edge_count
- tigergraph__run_loading_job_with_file
- tigergraph__run_loading_job_with_data

## Correct env vars

```text
TIGERGRAPH_MCP_ENABLED=true
TIGERGRAPH_MCP_COMMAND=tigergraph-mcp
TIGERGRAPH_MCP_ARGS=-vv

TG_HOST=http://127.0.0.1
TG_GRAPHNAME=iPerformInsights
TG_USERNAME=tigergraph
TG_PASSWORD=tigergraph
TG_API_TOKEN=
TG_PROFILE=
```

## Multiple profiles

```text
TG_PROFILE=prod

PROD_TG_HOST=https://prod.example.com
PROD_TG_API_TOKEN=...
PROD_TG_GRAPHNAME=iPerformInsights
PROD_TG_TGCLOUD=true
```

## Existing connection mode

Use:

```bash
uv run python scripts/run_tigergraph_mcp_with_existing_connection.py
```

## Validation

```bash
uv run python scripts/validate_tigergraph_corrected_source_of_truth.py
uv run python scripts/tigergraph_mcp_discover_tools.py
uv run python scripts/tigergraph_mcp_official_smoke_test.py
```
