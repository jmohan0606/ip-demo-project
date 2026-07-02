from __future__ import annotations

from app.graph.tigergraph.mcp_client import TigerGraphMcpClient


def main() -> None:
    client = TigerGraphMcpClient()
    if not client.is_configured():
        print("TigerGraph MCP is not configured. Set ENABLE_TIGERGRAPH_MCP=true and TIGERGRAPH_MCP_URL or stdio settings.")
        return
    tools = client.list_tools()
    print("TigerGraph MCP tools:")
    print(tools)


if __name__ == "__main__":
    main()
