from app.services.tigergraph_foundation_service import TigerGraphFoundationService


def test_tigergraph_inventory():
    service = TigerGraphFoundationService()
    inventory = service.get_schema_inventory()
    assert inventory.graph_name == "iperform_insights_coaching_demo"
    assert inventory.schema_prefix == "phx_dm_"
    assert len(inventory.vertices) >= 40
    assert all(v.name.startswith("phx_dm_") for v in inventory.vertices)


def test_prefix_validation():
    result = TigerGraphFoundationService().validate_prefix_convention()
    assert result["valid"] is True
