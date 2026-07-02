from __future__ import annotations
import json
from app.ingestion.tigergraph_upsert import TigerGraphUpsertClient
from app.models.memory import ContextMemory, ConversationTurn, ReasoningTrace

class TigerGraphMemoryLinker:
    def __init__(self) -> None:
        self.upsert = TigerGraphUpsertClient()

    def upsert_memory(self, memory: ContextMemory) -> dict:
        payload = {
            "memory_id": memory.memory_id,
            "memory_type": memory.memory_type.value,
            "scope_type": memory.scope_type.value,
            "scope_id": memory.scope_id,
            "title": memory.title,
            "summary": memory.summary,
            "facts_json": json.dumps(memory.facts),
            "confidence": memory.confidence,
            "valid_from": memory.valid_from.isoformat(),
            "valid_to": memory.valid_to.isoformat() if memory.valid_to else "",
            "created_ts": memory.created_ts.isoformat(),
            "source": memory.source,
            "status": memory.status,
        }
        result = self.upsert.upsert_vertex("phx_dm_context_memory", memory.memory_id, payload)
        edge_map = {
            "Firm": "phx_dm_memory_for_firm",
            "Division": "phx_dm_memory_for_division",
            "Region": "phx_dm_memory_for_region",
            "Market": "phx_dm_memory_for_market",
            "Advisor": "phx_dm_memory_for_advisor",
            "Household": "phx_dm_memory_for_household",
        }
        edge_type = edge_map.get(memory.scope_type.value)
        if edge_type:
            self.upsert.upsert_edge(edge_type, memory.memory_id, memory.scope_id, {})
        return result

    def upsert_conversation_turn(self, turn: ConversationTurn, memory_id: str | None = None) -> dict:
        payload = turn.model_dump()
        payload["turn_ts"] = turn.turn_ts.isoformat()
        payload["scope_type"] = turn.scope_type.value
        result = self.upsert.upsert_vertex("phx_dm_conversation_turn", turn.conversation_turn_id, payload)
        if memory_id:
            self.upsert.upsert_edge("phx_dm_conversation_created_memory", turn.conversation_turn_id, memory_id, {})
        return result

    def upsert_reasoning_trace(self, trace: ReasoningTrace, memory_ids: list[str] | None = None) -> dict:
        payload = {
            "trace_id": trace.trace_id,
            "trace_type": trace.trace_type,
            "conclusion": trace.conclusion,
            "confidence": trace.confidence,
            "reasoning_steps_json": json.dumps(trace.reasoning_steps),
            "evidence_json": json.dumps(trace.evidence),
            "created_ts": trace.created_ts.isoformat(),
            "status": trace.status,
        }
        result = self.upsert.upsert_vertex("phx_dm_reasoning_trace", trace.trace_id, payload)
        for memory_id in memory_ids or []:
            self.upsert.upsert_edge("phx_dm_reasoning_used_memory", trace.trace_id, memory_id, {})
        return result
