from app.models.memory import ContextMemoryCreateRequest, MemoryRetrievalRequest, MemoryScopeType, MemoryType
from app.services.context_service import ContextService
from app.services.memory_service import MemoryService

def test_create_and_retrieve_memory():
    service = MemoryService()
    memory = service.create_memory(
        ContextMemoryCreateRequest(
            memory_type=MemoryType.ADVISOR,
            scope_type=MemoryScopeType.ADVISOR,
            scope_id="ADV_UNIT",
            title="Unit memory",
            summary="Unit test memory",
            facts={"unit": True},
        ),
        write_to_graph=False,
    )
    assert memory.memory_id
    memories = service.retrieve_memories(
        MemoryRetrievalRequest(scope_type=MemoryScopeType.ADVISOR, scope_id="ADV_UNIT", limit=5)
    )
    assert len(memories) >= 1

def test_context_package():
    package = ContextService().build_context_package(
        MemoryRetrievalRequest(scope_type=MemoryScopeType.ADVISOR, scope_id="ADV_UNIT", limit=5)
    )
    assert package.scope_id == "ADV_UNIT"
