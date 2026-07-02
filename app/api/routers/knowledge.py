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

@router.get("/documents")
def documents():
    return ok(data=KnowledgeManagementService().list_documents())
