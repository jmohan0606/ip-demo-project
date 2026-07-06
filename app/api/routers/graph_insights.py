from fastapi import APIRouter

from app.ml import graph_algorithms as ga
from app.shared.responses import ok

router = APIRouter(prefix="/graph-insights", tags=["Graph Algorithms (GDS)"])


@router.post("/recompute")
def recompute():
    """Run PageRank + Louvain over the real graph and persist to graph_metrics (§6)."""
    return ok(data=ga.compute())


@router.get("/referral/{advisor_id}")
def referral_position(advisor_id: str):
    """Referral Network Position (PageRank percentile) for one advisor."""
    return ok(data=ga.referral_position(advisor_id))


@router.get("/communities")
def communities():
    """Detected peer communities (Louvain) with membership + distinguishing features."""
    return ok(data=ga.peer_communities())
