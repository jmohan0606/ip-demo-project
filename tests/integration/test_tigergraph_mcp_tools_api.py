from fastapi.testclient import TestClient
from app.api.main import app


def test_mcp_tools_endpoint_exists():
    client = TestClient(app)
    response = client.get("/graph-access/mcp-tools")
    # If MCP is not configured, endpoint may return error payload depending settings,
    # but route should exist and not be a 404.
    assert response.status_code != 404
