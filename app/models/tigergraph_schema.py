from __future__ import annotations

from pydantic import BaseModel, Field


class TigerGraphSchemaObject(BaseModel):
    name: str
    object_type: str
    description: str | None = None


class TigerGraphSchemaInventory(BaseModel):
    graph_name: str = "iperform_insights_coaching_demo"
    schema_prefix: str = "phx_dm_"
    vertices: list[TigerGraphSchemaObject] = Field(default_factory=list)
    edges: list[TigerGraphSchemaObject] = Field(default_factory=list)
    queries: list[TigerGraphSchemaObject] = Field(default_factory=list)
