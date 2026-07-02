from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.memory import get_memory_runtime
from app.shared.responses import ok

router = APIRouter(prefix="/memory-runtime", tags=["Memory Runtime"])


class MemoryContext(BaseModel):
    persona: str = "Advisor"
    scope_type: str = "Advisor"
    scope_id: str = "ADV0001"
    period: str = "YTD"
    compare_to: str = "Prior Year"


class MemoryWriteRequest(MemoryContext):
    memory_type: str = "Episodic"
    title: str = "Memory Event"
    content: str = ""
    importance: float = 0.7
    tags: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class ContextPacketRequest(MemoryContext):
    query: str = "Why did revenue decline and what should I do next?"
    max_tokens: int = 900


@router.get("/status")
def status():
    return ok(data=get_memory_runtime().status())


@router.post("/write")
def write_memory(request: MemoryWriteRequest):
    return ok(data=get_memory_runtime().write_memory(request.model_dump()))


@router.post("/retrieve")
def retrieve_memory(request: ContextPacketRequest):
    return ok(data=get_memory_runtime().retrieve_memory(request.model_dump(), request.query))


@router.post("/context")
def context_packet(request: ContextPacketRequest):
    return ok(data=get_memory_runtime().build_context_packet(request.model_dump(), request.query, request.max_tokens))
