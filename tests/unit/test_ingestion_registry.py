from app.ingestion.entity_registry import get_entity_config, list_entity_configs


def test_entity_registry_has_core_entities():
    names = {c.entity_name for c in list_entity_configs()}
    assert "advisor" in names
    assert "transaction" in names
    assert "recommendation" in names
    assert "memory" in names


def test_advisor_config():
    config = get_entity_config("advisor")
    assert config.tigergraph_vertex == "phx_dm_advisor"
    assert config.primary_key == "advisor_id"
