from __future__ import annotations

from fastapi import APIRouter

from app.client360.service import Client360Service
from app.shared.responses import ok

router = APIRouter(prefix="/client", tags=["Client 360"])


@router.get("/households/{advisor_id}")
def households(advisor_id: str):
    """Households served by an advisor (for the client picker)."""
    return ok(data={"households": Client360Service().households_for_advisor(advisor_id)})


@router.get("/360/{household_id}")
def client_360(household_id: str):
    """Full household/client profile: accounts, holdings, transactions, serving
    advisor and AI recommendations."""
    return ok(data=Client360Service().profile(household_id))
