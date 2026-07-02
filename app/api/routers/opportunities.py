from __future__ import annotations

from fastapi import APIRouter

from app.models.opportunities import OpportunityRunRequest, OpportunitySearchRequest
from app.services.opportunity_service import OpportunityService
from app.shared.responses import ok

router = APIRouter(prefix="/opportunities", tags=["Opportunity Engine"])


@router.post("/run")
def run_opportunities(request: OpportunityRunRequest):
    return ok(data=OpportunityService().run_opportunities(request).model_dump())


@router.post("/search")
def search_opportunities(request: OpportunitySearchRequest):
    return ok(data=OpportunityService().list_opportunities(request))


@router.get("/counts")
def counts():
    return ok(data=OpportunityService().counts())
