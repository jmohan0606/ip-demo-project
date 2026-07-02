from __future__ import annotations
from app.models.memory import ContextPackage, MemoryRetrievalRequest
from app.services.memory_service import MemoryService

class ContextService:
    def __init__(self) -> None:
        self.memory_service = MemoryService()

    def build_context_package(self, request: MemoryRetrievalRequest) -> ContextPackage:
        memories = self.memory_service.retrieve_memories(request)
        selected = memories[:request.limit]
        summary_parts = [f"- {m.memory_type.value}: {m.summary} (confidence={m.confidence})" for m in selected]
        context_summary = "\n".join(summary_parts) if summary_parts else "No relevant memories found."
        return ContextPackage(
            scope_type=request.scope_type,
            scope_id=request.scope_id,
            query=request.query,
            memories=selected,
            context_summary=context_summary,
            evidence_count=len(selected),
        )
