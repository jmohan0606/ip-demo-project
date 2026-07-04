from fastapi import APIRouter

from app.embeddings.service import EmbeddingSimilarityService
from app.shared.responses import ok

router = APIRouter(prefix="/embeddings", tags=["Graph Embeddings & Similarity"])


@router.post("/build")
def build_embeddings():
    service = EmbeddingSimilarityService()
    build = service.build_advisor_embeddings()
    matches = service.build_similarity_matches()
    return ok(data={"embeddings": build, "similarity": matches})


@router.get("/similar/{advisor_id}")
def similar_advisors(advisor_id: str, top_k: int = 5):
    return ok(data=EmbeddingSimilarityService().similar_advisors(advisor_id, top_k))


@router.get("/projection/{advisor_id}")
def projection(advisor_id: str, top_k: int = 5):
    """PCA 2D projection of the real persisted embedding vectors for the scatter plot."""
    return ok(data=EmbeddingSimilarityService().projection(advisor_id, top_k))
