from app.config.constants import APP_DISPLAY_NAME, GRAPH_NAME, SCHEMA_PREFIX
from app.config.settings import get_settings

def test_locked_constants():
    assert APP_DISPLAY_NAME == "iPerform Insights & Coaching"
    assert GRAPH_NAME == "iperform_insights_coaching_demo"
    assert SCHEMA_PREFIX == "phx_dm_"

def test_settings_defaults():
    settings = get_settings()
    assert settings.tigergraph_graph == GRAPH_NAME
    assert settings.tigergraph_schema_prefix == SCHEMA_PREFIX
