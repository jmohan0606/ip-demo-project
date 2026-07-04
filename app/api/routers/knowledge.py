from __future__ import annotations

from fastapi import APIRouter
from app.models.knowledge import KnowledgeIngestionRequest, KnowledgeSearchRequest
from app.services.knowledge_management_service import KnowledgeManagementService
from app.shared.responses import ok

router = APIRouter(prefix="/knowledge", tags=["Knowledge Management"])

@router.post("/ingest")
def ingest_document(request: KnowledgeIngestionRequest):
    return ok(data=KnowledgeManagementService().ingest_document(request).model_dump())

@router.post("/ingest-samples")
def ingest_samples():
    return ok(data=[r.model_dump() for r in KnowledgeManagementService().ingest_sample_knowledge()])

@router.post("/search")
def search(request: KnowledgeSearchRequest):
    return ok(data=KnowledgeManagementService().search(request).model_dump())

@router.post("/ask")
def ask(request: KnowledgeSearchRequest):
    """Full RAG: retrieve top-k -> grounded prompt -> LLMClient -> answer + cited sources."""
    from app.knowledge.rag_service import RagGenerationService
    return ok(data=RagGenerationService().answer(
        question=request.query,
        top_k=request.top_k,
        collection_name=request.collection_name,
        document_category=request.document_category,
    ))

@router.get("/documents")
def documents():
    return ok(data=KnowledgeManagementService().list_documents())
