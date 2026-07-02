from __future__ import annotations
from app.config.constants import APP_DISPLAY_NAME, GRAPH_NAME, SCHEMA_PREFIX
from app.config.settings import get_settings
from app.feature_store.sqlite_manager import SQLiteManager


def main() -> None:
    settings = get_settings()
    settings.ensure_local_directories()
    SQLiteManager().initialize_foundation_tables()
    assert APP_DISPLAY_NAME == "iPerform Insights & Coaching"
    assert GRAPH_NAME == "iperform_insights_coaching_demo"
    assert SCHEMA_PREFIX == "phx_dm_"
    assert settings.tigergraph_graph == GRAPH_NAME
    assert settings.tigergraph_schema_prefix == SCHEMA_PREFIX
    print("Foundation validation passed.")
    print(f"Application: {APP_DISPLAY_NAME}")
    print(f"Graph: {GRAPH_NAME}")
    print(f"Schema prefix: {SCHEMA_PREFIX}")


if __name__ == "__main__":
    main()
