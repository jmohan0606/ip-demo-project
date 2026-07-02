from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.ui_integrated_expanded_service import (
    get_advisor_360_data,
    get_recommendations_workspace_data,
    get_graph_explorer_data,
    get_features_embeddings_data,
    get_memory_explainability_data,
    search_knowledge,
)
from app.shared.responses import ok

router = APIRouter(prefix="/ui-integrated", tags=["Integrated UI Expanded"])


class UiContext(BaseModel):
    persona: str = "Advisor"
    scope_type: str = "Advisor"
    scope_id: str = "ADV0001"
    period: str = "YTD"
    compare_to: str = "Prior Year"


class KnowledgeSearchRequest(UiContext):
    query: str = "managed account growth playbook"


@router.post("/advisor-360")
def advisor_360(context: UiContext):
    return ok(data=get_advisor_360_data(context.model_dump()))


@router.post("/recommendations/workspace")
def recommendations_workspace(context: UiContext):
    return ok(data=get_recommendations_workspace_data(context.model_dump()))


@router.post("/graph/explore")
def graph_explore(context: UiContext):
    return ok(data=get_graph_explorer_data(context.model_dump()))


@router.post("/features-embeddings")
def features_embeddings(context: UiContext):
    return ok(data=get_features_embeddings_data(context.model_dump()))


@router.post("/memory-explainability")
def memory_explainability(context: UiContext):
    return ok(data=get_memory_explainability_data(context.model_dump()))


@router.post("/knowledge/search")
def knowledge_search(request: KnowledgeSearchRequest):
    return ok(data=search_knowledge(request.model_dump()))
