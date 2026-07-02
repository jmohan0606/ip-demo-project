from __future__ import annotations

from app.services.graph_access_service import GraphAccessService


def main() -> None:
    service = GraphAccessService()
    health = service.health()
    assert health["active_mode"] in {"mcp", "rest", "mock", "unavailable"}
    assert health["mock_available"] is True, health

    upsert = service.upsert_vertex(
        "phx_dm_context_memory",
        "MEM_VALIDATE_GRAPH_ACCESS",
        {
            "memory_id": "MEM_VALIDATE_GRAPH_ACCESS",
            "memory_type": "Advisor Memory",
            "scope_type": "Advisor",
            "scope_id": "ADV0001",
            "summary": "Validation memory",
            "status": "Active",
        },
    )
    assert upsert["success"] is True, upsert

    query = service.run_installed_query(
        "phx_dm_getInsightEvidenceForAdvisor",
        {"advisorId": "ADV0001", "advisor_id": "ADV0001"},
    )
    assert query["success"] is True, query

    print("TigerGraph MCP-first graph access validation passed.")
    print("Active mode:", health["active_mode"])
    print("Attempted upsert mode:", upsert["mode"])
    print("Attempted query mode:", query["mode"])


if __name__ == "__main__":
    main()
