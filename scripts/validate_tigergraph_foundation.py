from __future__ import annotations

from pathlib import Path

from app.services.tigergraph_foundation_service import TigerGraphFoundationService


def main() -> None:
    service = TigerGraphFoundationService()
    inventory = service.get_schema_inventory()
    prefix_result = service.validate_prefix_convention()

    assert inventory.graph_name == "iperform_insights_coaching_demo"
    assert inventory.schema_prefix == "phx_dm_"
    assert len(inventory.vertices) >= 40
    assert len(inventory.queries) >= 8
    assert prefix_result["valid"] is True

    required_files = [
        "tigergraph/schema/01_vertices.gsql",
        "tigergraph/schema/02_edges.gsql",
        "tigergraph/schema/03_create_graph.gsql",
        "tigergraph/queries_v1/phx_dm_validateGraphCounts.gsql",
    ]
    for file in required_files:
        assert Path(file).exists(), f"Missing required file: {file}"

    print("TigerGraph foundation validation passed.")
    print(f"Vertices: {len(inventory.vertices)}")
    print(f"Queries: {len(inventory.queries)}")


if __name__ == "__main__":
    main()
