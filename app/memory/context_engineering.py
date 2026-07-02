from __future__ import annotations

from typing import Any


class ContextEngineeringService:
    def estimate_tokens(self, text: str) -> int:
        return max(1, len(text.split()) * 4 // 3)

    def rank_memories(self, memories: list[dict[str, Any]], query: str, max_items: int = 8) -> list[dict[str, Any]]:
        query_terms = set(query.lower().split())
        ranked = []
        for memory in memories:
            text = f"{memory.get('title', '')} {memory.get('content', '')}".lower()
            overlap = sum(1 for term in query_terms if term in text)
            score = memory.get("importance", 0.5) + overlap * 0.15
            enriched = {**memory, "context_score": round(score, 4)}
            ranked.append(enriched)
        ranked.sort(key=lambda item: item["context_score"], reverse=True)
        return ranked[:max_items]

    def prune_context(self, items: list[dict[str, Any]], max_tokens: int = 900) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        selected = []
        used = 0
        dropped = 0
        for item in items:
            text = f"{item.get('title', '')}: {item.get('content', item.get('snippet', ''))}"
            tokens = self.estimate_tokens(text)
            if used + tokens <= max_tokens:
                selected.append(item)
                used += tokens
            else:
                dropped += 1
        return selected, {"max_tokens": max_tokens, "used_tokens": used, "dropped_items": dropped, "selected_items": len(selected)}

    def compress(self, memories: list[dict[str, Any]], knowledge: list[dict[str, Any]], graph: list[dict[str, Any]]) -> str:
        parts = []
        if memories:
            parts.append("Relevant memory:")
            parts.extend([f"- [{m.get('memory_type')}] {m.get('title')}: {m.get('content')}" for m in memories[:5]])
        if knowledge:
            parts.append("Relevant knowledge:")
            parts.extend([f"- {k.get('title')}: {k.get('snippet')}" for k in knowledge[:5]])
        if graph:
            parts.append("Graph evidence:")
            parts.extend([f"- {g.get('source', 'Graph')}: {g.get('summary', g.get('item', 'Evidence'))}" for g in graph[:5]])
        return "\n".join(parts)
