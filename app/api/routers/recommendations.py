from __future__ import annotations

from fastapi import APIRouter

from app.models.recommendations import RecommendationActionRequest, RecommendationRunRequest, RecommendationSearchRequest
from app.services.recommendation_service import RecommendationService
from app.shared.responses import ok

router = APIRouter(prefix="/recommendations", tags=["Recommendation Engine"])


@router.post("/run")
def run_recommendations(request: RecommendationRunRequest):
    return ok(data=RecommendationService().run_recommendations(request).model_dump())


@router.post("/search")
def search_recommendations(request: RecommendationSearchRequest):
    return ok(data=RecommendationService().list_recommendations(request))


@router.post("/status")
def update_status(request: RecommendationActionRequest):
    return ok(data=RecommendationService().update_status(request))


@router.get("/counts")
def counts():
    return ok(data=RecommendationService().counts())
