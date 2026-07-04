from __future__ import annotations

from fastapi import APIRouter

from app.graph.neighborhood import advisor_neighborhood
from app.shared.responses import ok

router = APIRouter(prefix="/graph-viz", tags=["Graph Explorer"])


@router.get("/neighborhood")
def neighborhood(advisor_id: str = "A001"):
    """Real one-hop subgraph around an advisor (households, CRM, AGP, AI artifacts)
    for the Knowledge Graph Explorer canvas."""
    return ok(data=advisor_neighborhood(advisor_id))
