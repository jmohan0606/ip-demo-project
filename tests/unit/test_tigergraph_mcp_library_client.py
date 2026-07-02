from app.graph.tigergraph.mcp_library_client import TigerGraphMcpLibraryClient
from app.graph.tigergraph.mcp_client import TigerGraphMcpClient


def test_mcp_library_client_constructs():
    client = TigerGraphMcpLibraryClient()
    assert client is not None


def test_mcp_wrapper_constructs():
    client = TigerGraphMcpClient()
    assert client is not None
