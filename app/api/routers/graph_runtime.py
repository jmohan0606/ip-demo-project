from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.graph import get_graph_runtime
from app.shared.responses import ok

router = APIRouter(prefix="/graph-runtime", tags=["Graph Runtime"])


class QueryRequest(BaseModel):
    query_name: str = "get_advisor_context"
    params: dict = Field(default_factory=dict)


class VertexRequest(BaseModel):
    vertex_type: str
    vertex_id: str
    attributes: dict = Field(default_factory=dict)


class EdgeRequest(BaseModel):
    edge_type: str
    from_type: str
    from_id: str
    to_type: str
    to_id: str
    attributes: dict = Field(default_factory=dict)


class RecommendationFeedbackRequest(BaseModel):
    recommendation_id: str
    action: str
    notes: str | None = None
    created_at: str | None = None


@router.get("/status")
def status():
    return ok(data=get_graph_runtime().status())


@router.post("/query")
def query(request: QueryRequest):
    return ok(data=get_graph_runtime().execute_query(request.query_name, request.params).to_dict())


@router.post("/vertex")
def vertex(request: VertexRequest):
    return ok(data=get_graph_runtime().upsert_vertex(request.vertex_type, request.vertex_id, request.attributes).to_dict())


@router.post("/edge")
def edge(request: EdgeRequest):
    return ok(data=get_graph_runtime().upsert_edge(
        request.edge_type,
        request.from_type,
        request.from_id,
        request.to_type,
        request.to_id,
        request.attributes,
    ).to_dict())


@router.post("/feedback")
def feedback(request: RecommendationFeedbackRequest):
    return ok(data=get_graph_runtime().persist_recommendation_feedback(request.model_dump()).to_dict())
