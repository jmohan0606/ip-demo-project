from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from app.knowledge.embedding_provider import DeterministicEmbeddingProvider
from app.knowledge.models import DocumentChunk, KnowledgeResult


class MockPersistentVectorStore:
    """Small JSON-backed vector store fallback compatible with local demo mode."""

    def __init__(self, persist_dir: str, collection_name: str) -> None:
        self.persist_dir = Path(persist_dir)
        self.collection_name = collection_name
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.persist_dir / f"{collection_name}_mock_vectors.json"
        self.embedder = DeterministicEmbeddingProvider()
        self.records: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            self.records = json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self) -> None:
        self.path.write_text(json.dumps(self.records, indent=2), encoding="utf-8")

    def count(self) -> int:
        return len(self.records)

    def upsert_chunks(self, chunks: list[DocumentChunk]) -> dict[str, Any]:
        existing_ids = {record["chunk_id"] for record in self.records}
        inserted = 0
        for chunk in chunks:
            record = {
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "document_name": chunk.document_name,
                "chunk_index": chunk.chunk_index,
                "text": chunk.text,
                "metadata": chunk.metadata,
                "embedding": self.embedder.embed(chunk.text),
            }
            if chunk.chunk_id in existing_ids:
                self.records = [record if item["chunk_id"] == chunk.chunk_id else item for item in self.records]
            else:
                self.records.append(record)
                inserted += 1
        self._save()
        return {"upserted": len(chunks), "inserted": inserted, "collection_count": self.count()}

    def search(self, query: str, top_k: int = 5) -> list[KnowledgeResult]:
        query_vec = self.embedder.embed(query)
        scored = []
        for record in self.records:
            score = self._cosine(query_vec, record["embedding"])
            scored.append((score, record))
        scored.sort(key=lambda item: item[0], reverse=True)

        if not scored:
            demo_records = [
                ("Managed Account Growth Playbook", "Use suitability-backed reviews to identify managed account expansion opportunities."),
                ("NNM Recovery Conversation Guide", "Outflow recovery should start with liquidity need confirmation and follow-up planning."),
                ("AGP Coaching Framework", "AGP advisors require weekly coaching actions and milestone tracking."),
            ]
            return [
                KnowledgeResult(title=title, source="mock_vector_store", score=0.92 - i * 0.06, snippet=snippet, metadata={"fallback": True})
                for i, (title, snippet) in enumerate(demo_records[:top_k])
            ]

        return [
            KnowledgeResult(
                title=record["document_name"],
                source="mock_vector_store",
                score=round(float(score), 4),
                snippet=record["text"][:240],
                metadata={"chunk_id": record["chunk_id"], "document_id": record["document_id"], **record.get("metadata", {})},
            )
            for score, record in scored[:top_k]
        ]

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        an = math.sqrt(sum(x * x for x in a)) or 1.0
        bn = math.sqrt(sum(y * y for y in b)) or 1.0
        return dot / (an * bn)
