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


@router.get("/similar/{entity_type}/{entity_id}")
def similar(entity_type: str, entity_id: str, top_k: int = 5, model: str | None = None):
    """Nearest entities by GNN embedding cosine (Section 11.1 §7/§8, VectorClient).
    Optional ?model=graphsage-v1|graphsage-v1-ft to compare before/after outcome fine-tuning
    (Section 11.3); default = the active model per the registry."""
    from app.ml import registry
    from app.ml.vector_client import get_vector_client

    vc = get_vector_client()
    resolved = model or registry.active_embedding_model()
    vec = vc.get(entity_type, entity_id, model_name=resolved)
    if vec is None:
        return ok(data={"available": False, "entity_type": entity_type, "entity_id": entity_id, "model": resolved})
    return ok(data={"available": True, "entity_type": entity_type, "entity_id": entity_id, "model": resolved,
                    "backend": vc.describe(), "matches": vc.search(entity_type, vec, top_k, exclude_id=entity_id, model_name=resolved)})
