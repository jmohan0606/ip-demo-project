from __future__ import annotations

from fastapi import APIRouter
from app.models.embeddings import EmbeddingBuildRequest, SimilaritySearchRequest
from app.services.embedding_similarity_service import EmbeddingSimilarityService
from app.shared.responses import ok

router = APIRouter(prefix="/embeddings", tags=["Graph Embeddings & Similarity"])


@router.post("/build")
def build_embeddings(request: EmbeddingBuildRequest):
    return ok(data=EmbeddingSimilarityService().build_embeddings_and_similarity(request).model_dump())


@router.get("/list")
def list_embeddings(entity_type: str | None = None, limit: int = 100):
    return ok(data=EmbeddingSimilarityService().list_embeddings(entity_type, limit))


@router.post("/similarity/search")
def search_similarity(request: SimilaritySearchRequest):
    return ok(data=EmbeddingSimilarityService().search_similarity(request))


@router.get("/similarity/list")
def list_similarity(limit: int = 100):
    return ok(data=EmbeddingSimilarityService().list_similarity(limit))


@router.get("/counts")
def counts():
    return ok(data=EmbeddingSimilarityService().counts())
