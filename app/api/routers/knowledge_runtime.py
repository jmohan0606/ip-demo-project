from __future__ import annotations

from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel, Field

from app.knowledge import get_knowledge_runtime
from app.shared.responses import ok

router = APIRouter(prefix="/knowledge-runtime", tags=["Knowledge Runtime"])


class KnowledgeSearchRequest(BaseModel):
    query: str = "managed account growth playbook"
    top_k: int = 5


class KnowledgeIngestRequest(BaseModel):
    document_name: str = "advisor_playbook_demo.txt"
    document_type: str = "playbook"
    content: str = ""
    metadata: dict = Field(default_factory=dict)


@router.get("/status")
def status():
    return ok(data=get_knowledge_runtime().status().to_dict())


@router.post("/search")
def search(request: KnowledgeSearchRequest):
    return ok(data=get_knowledge_runtime().search(request.query, request.top_k).to_dict())


@router.post("/ingest")
def ingest(request: KnowledgeIngestRequest):
    return ok(data=get_knowledge_runtime().ingest_document(
        document_name=request.document_name,
        document_type=request.document_type,
        content=request.content,
        metadata=request.metadata,
    ).to_dict())


@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    document_type: str = Form(default="playbook"),
):
    raw = await file.read()
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        content = raw.decode("latin-1", errors="ignore")

    return ok(data=get_knowledge_runtime().ingest_document(
        document_name=file.filename or "uploaded_document.txt",
        document_type=document_type,
        content=content,
        metadata={"upload_content_type": file.content_type or "unknown"},
    ).to_dict())
