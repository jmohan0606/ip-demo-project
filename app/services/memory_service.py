from __future__ import annotations
from app.graph.memory.tigergraph_memory_linker import TigerGraphMemoryLinker
from app.models.memory import (
    ContextMemory, ContextMemoryCreateRequest, ConversationTurn, ConversationTurnCreateRequest,
    MemoryRetrievalRequest, ReasoningTrace, ReasoningTraceCreateRequest, MemoryType
)
from app.repositories.state_repository import get_state_repository
from app.shared.ids import timestamp_id

class MemoryService:
    """All memory persistence now flows through the StateRepository adapter, so
    TigerGraph is the source of truth (with SQLite fallback) rather than SQLite direct.
    `write_to_graph` is retained for callers that only want the SQLite mirror (e.g. the
    seeder's non-graph rows); the adapter still writes both tiers by default."""

    def __init__(self) -> None:
        self.state = get_state_repository()
        # Kept for the dedicated conversation-turn / reasoning-trace vertex + edge links
        # that the memory linker adds beyond the context_memory vertex.
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
        self.state.save_memory(memory)
        return memory

    def retrieve_memories(self, request: MemoryRetrievalRequest) -> list[ContextMemory]:
        return self.state.retrieve_memories(
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
        self.state.save_conversation_turn(turn)
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
        )
        # link the conversation-turn vertex to its context-memory vertex in the graph.
        if write_to_graph:
            try:
                self.linker.upsert_conversation_turn(turn, memory.memory_id)
            except Exception:  # noqa: BLE001 — link is best-effort; turn already persisted
                pass
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
        self.state.save_reasoning_trace(trace)
        # Anchor this trace into the SAME canonical representation the pipeline uses, so a
        # memory-service trace is discoverable by the explainability lineage exactly like a
        # prediction/opportunity/recommendation trace. artifact_type/artifact_id + the
        # matching `phx_dm_reasoning_for_*` edge come from whichever artifact the request cites.
        artifact_type, artifact_id, artifact_edge = None, None, None
        if request.recommendation_id:
            artifact_type, artifact_id, artifact_edge = "RECOMMENDATION", request.recommendation_id, "phx_dm_reasoning_for_recommendation"
        elif request.prediction_id:
            artifact_type, artifact_id, artifact_edge = "PREDICTION", request.prediction_id, "phx_dm_reasoning_for_prediction"
        elif request.opportunity_id:
            artifact_type, artifact_id, artifact_edge = "OPPORTUNITY", request.opportunity_id, "phx_dm_reasoning_for_opportunity"
        if write_to_graph:
            try:
                # re-upsert with the resolved artifact linkage + canonical `_uses_memory` edges
                self.linker.upsert_reasoning_trace(
                    trace, memory_ids=request.memory_ids, artifact_type=artifact_type, artifact_id=artifact_id
                )
                if artifact_edge and artifact_id:
                    self.linker.upsert.upsert_edge(artifact_edge, trace.trace_id, artifact_id, {})
            except Exception:  # noqa: BLE001 — graph link is best-effort; trace already persisted
                pass
        return trace

    def memory_counts_by_type(self) -> list[dict]:
        return self.state.memory_counts_by_type()
