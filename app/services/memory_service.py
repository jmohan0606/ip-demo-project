from __future__ import annotations
from app.graph.memory.memory_repository import MemoryRepository
from app.graph.memory.tigergraph_memory_linker import TigerGraphMemoryLinker
from app.models.memory import (
    ContextMemory, ContextMemoryCreateRequest, ConversationTurn, ConversationTurnCreateRequest,
    MemoryRetrievalRequest, ReasoningTrace, ReasoningTraceCreateRequest, MemoryType
)
from app.shared.ids import timestamp_id

class MemoryService:
    def __init__(self) -> None:
        self.repo = MemoryRepository()
        self.linker = TigerGraphMemoryLinker()

    def create_memory(self, request: ContextMemoryCreateRequest, write_to_graph: bool = True) -> ContextMemory:
        memory = ContextMemory(
            memory_id=timestamp_id("mem"),
            memory_type=request.memory_type,
            scope_type=request.scope_type,
            scope_id=request.scope_id,
            title=request.title,
            summary=request.summary,
            facts=request.facts,
            confidence=request.confidence,
            source=request.source,
            valid_from=request.valid_from,
            valid_to=request.valid_to,
        )
        self.repo.save_memory(memory)
        if write_to_graph:
            self.linker.upsert_memory(memory)
        return memory

    def retrieve_memories(self, request: MemoryRetrievalRequest) -> list[ContextMemory]:
        return self.repo.retrieve_memories(
            request.scope_type, request.scope_id, request.memory_types, request.limit, request.include_expired
        )

    def save_conversation_turn(self, request: ConversationTurnCreateRequest, write_to_graph: bool = True) -> ConversationTurn:
        turn = ConversationTurn(
            conversation_turn_id=timestamp_id("turn"),
            conversation_id=request.conversation_id,
            user_question=request.user_question,
            assistant_answer=request.assistant_answer,
            persona=request.persona,
            scope_type=request.scope_type,
            scope_id=request.scope_id,
        )
        self.repo.save_conversation_turn(turn)
        memory = self.create_memory(
            ContextMemoryCreateRequest(
                memory_type=MemoryType.CONVERSATION,
                scope_type=request.scope_type,
                scope_id=request.scope_id,
                title=f"Conversation {request.conversation_id}",
                summary=f"Q: {request.user_question}\nA: {request.assistant_answer}",
                facts={"conversation_id": request.conversation_id},
                confidence=0.80,
                source="ai_assistant",
            ),
            write_to_graph=write_to_graph,
        )
        if write_to_graph:
            self.linker.upsert_conversation_turn(turn, memory.memory_id)
        return turn

    def save_reasoning_trace(self, request: ReasoningTraceCreateRequest, write_to_graph: bool = True) -> ReasoningTrace:
        trace = ReasoningTrace(
            trace_id=timestamp_id("trace"),
            trace_type=request.trace_type,
            conclusion=request.conclusion,
            confidence=request.confidence,
            reasoning_steps=request.reasoning_steps,
            evidence=request.evidence,
        )
        self.repo.save_reasoning_trace(trace)
        if write_to_graph:
            self.linker.upsert_reasoning_trace(trace, request.memory_ids)
        return trace

    def memory_counts_by_type(self) -> list[dict]:
        return self.repo.memory_counts_by_type()
