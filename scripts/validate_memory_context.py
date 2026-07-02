from __future__ import annotations
from app.models.memory import ContextMemoryCreateRequest, MemoryRetrievalRequest, MemoryScopeType, MemoryType
from app.services.context_service import ContextService
from app.services.memory_service import MemoryService

def main() -> None:
    service = MemoryService()
    memory = service.create_memory(
        ContextMemoryCreateRequest(
            memory_type=MemoryType.ADVISOR,
            scope_type=MemoryScopeType.ADVISOR,
            scope_id="ADV_TEST",
            title="Validation memory",
            summary="Advisor validation memory for context graph.",
            facts={"test": True},
            confidence=0.91,
        )
    )
    assert memory.memory_id
    package = ContextService().build_context_package(
        MemoryRetrievalRequest(scope_type=MemoryScopeType.ADVISOR, scope_id="ADV_TEST", limit=5)
    )
    assert package.evidence_count >= 1
    print("Context Graph & Temporal Memory validation passed.")
    print(f"Memory ID: {memory.memory_id}")
    print(f"Evidence count: {package.evidence_count}")

if __name__ == "__main__":
    main()
