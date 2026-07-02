from __future__ import annotations

from dataclasses import asdict
from uuid import uuid4

from app.config import get_runtime_config
from app.graph import get_graph_runtime
from app.knowledge import get_knowledge_runtime
from app.memory.context_engineering import ContextEngineeringService
from app.memory.memory_store import SQLiteMemoryStore
from app.memory.models import ContextPacket, MemoryEvent


class MemoryRuntime:
    def __init__(self) -> None:
        self.config = get_runtime_config()
        self.store = SQLiteMemoryStore(self.config.sqlite_db_path)
        self.context_engineering = ContextEngineeringService()
        self.graph = get_graph_runtime()
        self.knowledge = get_knowledge_runtime()
        self._seed_demo_memories()

    def _seed_demo_memories(self) -> None:
        demo = [
            MemoryEvent("MEM-DEMO-001", "Episodic", "ADV0001", "Advisor", "Revenue decline discussion", "Advisor asked why revenue declined in fixed income while managed account revenue improved.", 0.92, ["revenue", "fixed-income", "managed"]),
            MemoryEvent("MEM-DEMO-002", "Semantic", "ADV0001", "Advisor", "Managed account coaching preference", "Advisor prefers concise household action lists with compliance-safe next steps.", 0.88, ["coaching", "preference"]),
            MemoryEvent("MEM-DEMO-003", "Reasoning", "ADV0001", "Advisor", "NNM recovery reasoning", "Prior recommendation identified negative NCF households as first recovery target.", 0.84, ["nnm", "ncf", "reasoning"]),
            MemoryEvent("MEM-DEMO-004", "Procedural", "Global", "Global", "Recommendation feedback process", "Accept, reject, ignore, modify and complete actions should update learning signals and graph memory.", 0.81, ["feedback", "learning"]),
        ]
        for memory in demo:
            self.store.upsert_memory(memory)

    def status(self) -> dict:
        return {
            "memory_backend": "sqlite",
            "sqlite_db_path": self.config.sqlite_db_path,
            "counts": self.store.count(),
            "graph_runtime": self.graph.status(),
        }

    def write_memory(self, payload: dict) -> dict:
        memory = MemoryEvent(
            memory_id=payload.get("memory_id") or f"MEM-{uuid4().hex[:10].upper()}",
            memory_type=payload.get("memory_type", "Episodic"),
            scope_id=payload.get("scope_id", "ADV0001"),
            persona=payload.get("persona", "Advisor"),
            title=payload.get("title", "Memory Event"),
            content=payload.get("content", ""),
            importance=float(payload.get("importance", 0.7)),
            tags=payload.get("tags", []),
            metadata=payload.get("metadata", {}),
        )
        self.store.upsert_memory(memory)
        graph_result = self.graph.persist_memory_event(asdict(memory)).to_dict()
        return {"memory": asdict(memory), "graph_persistence": graph_result}

    def retrieve_memory(self, context: dict, query: str = "", limit: int = 10) -> dict:
        memories = self.store.search_memory(
            scope_id=context.get("scope_id", "ADV0001"),
            persona=context.get("persona", "Advisor"),
            query=query,
            limit=limit,
        )
        return {"query": query, "memories": memories}

    def build_context_packet(self, context: dict, query: str, max_tokens: int = 900) -> dict:
        raw_memories = self.store.search_memory(context.get("scope_id", "ADV0001"), context.get("persona", "Advisor"), query, 25)
        ranked = self.context_engineering.rank_memories(raw_memories, query, max_items=12)
        pruned_memories, pruning_summary = self.context_engineering.prune_context(ranked, max_tokens=max_tokens // 2)

        knowledge_result = self.knowledge.search(query, top_k=5).to_dict()
        knowledge_items = knowledge_result.get("data", {}).get("results", [])

        graph_result = self.graph.execute_query("get_advisor_context", {"advisor_id": context.get("scope_id", "ADV0001")}).to_dict()
        graph_evidence = [{"source": "GraphRuntime", "summary": graph_result.get("message", ""), "mode": graph_result.get("mode")}]

        compressed = self.context_engineering.compress(pruned_memories, knowledge_items, graph_evidence)
        token_estimate = self.context_engineering.estimate_tokens(compressed)

        packet = ContextPacket(
            context_id=f"CTX-{uuid4().hex[:10].upper()}",
            persona=context.get("persona", "Advisor"),
            scope_id=context.get("scope_id", "ADV0001"),
            period=context.get("period", "YTD"),
            user_question=query,
            selected_memories=pruned_memories,
            selected_knowledge=knowledge_items,
            selected_graph_evidence=graph_evidence,
            compressed_context=compressed,
            token_estimate=token_estimate,
            pruning_summary=pruning_summary,
        )
        packet_dict = asdict(packet)
        self.store.save_context_packet(packet_dict)

        self.graph.upsert_vertex("ContextPacket", packet.context_id, {
            "context_id": packet.context_id,
            "persona": packet.persona,
            "scope_id": packet.scope_id,
            "token_estimate": packet.token_estimate,
            "selected_memory_count": len(packet.selected_memories),
        })

        return packet_dict


_memory_runtime: MemoryRuntime | None = None


def get_memory_runtime() -> MemoryRuntime:
    global _memory_runtime
    if _memory_runtime is None:
        _memory_runtime = MemoryRuntime()
    return _memory_runtime
