from __future__ import annotations

from app.services.graph_access_service import GraphAccessService


def main() -> None:
    service = GraphAccessService()
    print("Graph health:")
    print(service.health())

    print("\nMock/MCP/REST installed query:")
    print(service.run_installed_query("phx_dm_getInsightEvidenceForAdvisor", {"advisorId": "ADV0001"}))

    print("\nSchema:")
    print(service.schema())


if __name__ == "__main__":
    main()
