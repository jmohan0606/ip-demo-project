from __future__ import annotations

from typing import Any

from app.graph.access.graph_access_client import GraphAccessClient


class TigerGraphUpsertClient:
    """Compatibility wrapper used by existing modules.

    Part 12.1 routes all writes through the MCP-first GraphAccessClient:
        MCP -> REST -> Mock
    """

    def __init__(self) -> None:
        self.graph = GraphAccessClient()

    def upsert_vertex(self, vertex_type: str, primary_key: str, attributes: dict[str, Any]) -> dict[str, Any]:
        result = self.graph.upsert_vertex(vertex_type, primary_key, attributes)
        if not result.success:
            raise RuntimeError(result.error or "Vertex upsert failed.")
        return result.model_dump()

    def upsert_edge(self, edge_type: str, from_id: str, to_id: str, attributes: dict[str, Any] | None = None) -> dict[str, Any]:
        result = self.graph.upsert_edge(edge_type, from_id, to_id, attributes or {})
        if not result.success:
            raise RuntimeError(result.error or "Edge upsert failed.")
        return result.model_dump()
