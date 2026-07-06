from __future__ import annotations
from fastapi import APIRouter
from app.models.memory import (
    ContextMemoryCreateRequest, ConversationTurnCreateRequest, MemoryRetrievalRequest, ReasoningTraceCreateRequest
)
from app.services.context_service import ContextService
from app.services.memory_service import MemoryService
from app.shared.responses import ok

router = APIRouter(prefix="/memory", tags=["Context Graph & Temporal Memory"])

@router.post("/create")
def create_memory(request: ContextMemoryCreateRequest):
    return ok(data=MemoryService().create_memory(request).model_dump())

@router.post("/retrieve")
def retrieve_memory(request: MemoryRetrievalRequest):
    return ok(data=[m.model_dump() for m in MemoryService().retrieve_memories(request)])

@router.post("/context-package")
def context_package(request: MemoryRetrievalRequest):
    return ok(data=ContextService().build_context_package(request).model_dump())

@router.post("/conversation-turn")
def conversation_turn(request: ConversationTurnCreateRequest):
    return ok(data=MemoryService().save_conversation_turn(request).model_dump())

@router.post("/reasoning-trace")
def reasoning_trace(request: ReasoningTraceCreateRequest):
    return ok(data=MemoryService().save_reasoning_trace(request).model_dump())

@router.get("/counts")
def memory_counts():
    return ok(data=MemoryService().memory_counts_by_type())


@router.post("/seed-types/{advisor_id}")
def seed_memory_types(advisor_id: str):
    """Populate the 4 previously-schema-only memory types (Semantic/Episodic/Procedural/
    Preference) for an advisor, grounded in real data (Section 11.6)."""
    from app.graph.memory.memory_seeder import seed_for_advisor
    return ok(data=seed_for_advisor(advisor_id))


@router.get("/audit")
def memory_audit(scope_id: str = "A001"):
    """Coverage of the 6 poster memory types for an advisor."""
    from app.graph.memory.memory_seeder import audit
    return ok(data=audit(scope_id))
