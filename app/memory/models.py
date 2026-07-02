from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MemoryEvent:
    memory_id: str
    memory_type: str
    scope_id: str
    persona: str
    title: str
    content: str
    importance: float
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextPacket:
    context_id: str
    persona: str
    scope_id: str
    period: str
    user_question: str
    selected_memories: list[dict[str, Any]]
    selected_knowledge: list[dict[str, Any]]
    selected_graph_evidence: list[dict[str, Any]]
    compressed_context: str
    token_estimate: int
    pruning_summary: dict[str, Any]
