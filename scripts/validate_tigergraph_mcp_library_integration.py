from __future__ import annotations

from app.graph.tigergraph.mcp_client import TigerGraphMcpClient
from app.graph.tigergraph.mcp_library_client import TigerGraphMcpLibraryClient
from app.services.graph_access_service import GraphAccessService


def main() -> None:
    library_client = TigerGraphMcpLibraryClient()
    wrapper = TigerGraphMcpClient()
    graph = GraphAccessService()

    health = graph.health()
    assert "active_mode" in health
    assert "strategy" in health

    # This does not require a live MCP server; it validates correct client wiring.
    print("TigerGraph MCP library integration validation passed.")
    print("Library client configured:", library_client.is_configured())
    print("Wrapper configured:", wrapper.is_configured())
    print("Graph access active mode:", health["active_mode"])
    print("Graph strategy:", health["strategy"])


if __name__ == "__main__":
    main()
