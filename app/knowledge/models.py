from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DocumentChunk:
    chunk_id: str
    document_id: str
    document_name: str
    chunk_index: int
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class KnowledgeResult:
    title: str
    source: str
    score: float
    snippet: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class KnowledgeRuntimeResult:
    status: str
    mode: str
    operation: str
    data: Any
    fallback_used: bool = False
    message: str = ""
    trace: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "mode": self.mode,
            "operation": self.operation,
            "data": self.data,
            "fallback_used": self.fallback_used,
            "message": self.message,
            "trace": self.trace,
        }
