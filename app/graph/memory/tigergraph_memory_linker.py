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

    def upsert_reasoning_trace(
        self,
        trace: ReasoningTrace,
        memory_ids: list[str] | None = None,
        artifact_type: str | None = None,
        artifact_id: str | None = None,
    ) -> dict:
        """Persist a reasoning trace in the ONE canonical `phx_dm_reasoning_trace` shape
        used by every display reader (get_reasoning_trace / get_memory_timeline / client360)
        AND the reuse reader (get_reasoning_traces_for_scope): PK `reasoning_id`, plus
        `artifact_type`/`artifact_id`/`created_at`. The memory-service semantics
        (trace_type/conclusion/status) are preserved: trace_type → artifact_type, and
        conclusion is appended as the terminal reasoning step (so the reuse reader, which
        takes steps[-1] as the conclusion, surfaces it) with the raw fields kept inside
        evidence_json. Memories link via `phx_dm_reasoning_uses_memory` — the canonical edge
        the readers traverse (the old `phx_dm_reasoning_used_memory` name was a dead edge:
        not in the manifest and never read)."""
        steps = list(trace.reasoning_steps)
        if trace.conclusion and (not steps or steps[-1] != trace.conclusion):
            steps.append(trace.conclusion)
        payload = {
            "reasoning_id": trace.trace_id,
            "artifact_type": (artifact_type or trace.trace_type or "").upper(),
            "artifact_id": artifact_id or "",
            "reasoning_steps_json": json.dumps(steps),
            "evidence_json": json.dumps({
                "evidence": trace.evidence,
                "trace_type": trace.trace_type,
                "conclusion": trace.conclusion,
                "status": trace.status,
                "confidence": trace.confidence,
            }),
            "model_name": "",
            "prompt_version": "",
            "confidence": trace.confidence,
            "created_at": trace.created_ts.isoformat(),
        }
        result = self.upsert.upsert_vertex("phx_dm_reasoning_trace", trace.trace_id, payload)
        for memory_id in memory_ids or []:
            self.upsert.upsert_edge("phx_dm_reasoning_uses_memory", trace.trace_id, memory_id, {})
        return result
