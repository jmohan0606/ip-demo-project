from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile
from app.config.settings import get_settings
from app.models.knowledge import KnowledgeIngestionRequest, KnowledgeSearchRequest
from app.services.knowledge_management_service import KnowledgeManagementService
from app.shared.responses import fail, ok

router = APIRouter(prefix="/knowledge", tags=["Knowledge Management"])

# The real parsers wired in Part 2A (pypdf / python-docx / python-pptx + txt).
SUPPORTED_UPLOAD_SUFFIXES = {".pdf", ".docx", ".pptx", ".txt", ".md"}

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

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    document_category: str | None = Form(default=None),
):
    """Real ingestion of an uploaded PDF/DOCX/PPTX/TXT: save -> parse -> chunk ->
    embed -> Chroma, the same path ingest_document takes. Returns the created
    document, chunk count and assigned category so the UI can show real results.
    """
    filename = Path(file.filename or "upload.txt").name
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_UPLOAD_SUFFIXES:
        return fail(
            message=f"Unsupported file type '{suffix}'. Supported: "
            f"{', '.join(sorted(SUPPORTED_UPLOAD_SUFFIXES))}.",
        )

    upload_dir = Path(get_settings().documents_path) / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / filename
    dest.write_bytes(await file.read())

    service = KnowledgeManagementService()
    category = document_category or service._category_for(filename)
    result = service.ingest_document(KnowledgeIngestionRequest(
        source_path=str(dest),
        document_category=category,
    ))
    return ok(data={
        "document_id": result.document.document_id,
        "document_name": result.document.document_name,
        "document_category": result.document.document_category,
        "chunks_created": len(result.chunks),
        "indexed_count": result.indexed_count,
        "collection_name": result.collection_name,
        "status": result.status,
        "message": result.message,
    })


@router.get("/documents")
def documents():
    return ok(data=KnowledgeManagementService().list_documents())
