from app.graph.access.graph_access_client import GraphAccessClient


def test_graph_access_health_available():
    health = GraphAccessClient().health()
    assert health.active_mode.value in {"mcp", "rest", "mock", "unavailable"}
    assert health.mock_available is True


def test_graph_access_mock_query():
    result = GraphAccessClient().run_installed_query("phx_dm_getInsightEvidenceForAdvisor", {"advisorId": "ADV0001"})
    assert result.success is True
    assert result.mode.value in {"mcp", "rest", "mock"}
