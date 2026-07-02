from __future__ import annotations

from pathlib import Path

from app.config.settings import get_settings
from app.graph.tigergraph.schema_inventory import build_schema_inventory
from app.models.tigergraph_schema import TigerGraphSchemaInventory


class TigerGraphFoundationService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.project_root = Path(__file__).resolve().parents[2]

    def get_schema_inventory(self) -> TigerGraphSchemaInventory:
        return build_schema_inventory()

    def list_schema_files(self) -> list[str]:
        schema_dir = self.project_root / "tigergraph" / "schema"
        return sorted(str(p.relative_to(self.project_root)) for p in schema_dir.glob("*.gsql"))

    def list_v1_query_files(self) -> list[str]:
        query_dir = self.project_root / "tigergraph" / "queries_v1"
        return sorted(str(p.relative_to(self.project_root)) for p in query_dir.glob("*.gsql"))

    def validate_prefix_convention(self) -> dict:
        inventory = self.get_schema_inventory()
        bad_vertices = [v.name for v in inventory.vertices if not v.name.startswith("phx_dm_")]
        bad_queries = [q.name for q in inventory.queries if not q.name.startswith("phx_dm_")]
        return {
            "valid": not bad_vertices and not bad_queries,
            "bad_vertices": bad_vertices,
            "bad_queries": bad_queries,
            "schema_prefix": self.settings.tigergraph_schema_prefix,
            "graph_name": self.settings.tigergraph_graph,
        }
