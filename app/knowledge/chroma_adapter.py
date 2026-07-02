from __future__ import annotations

from typing import Any

from app.knowledge.embedding_provider import DeterministicEmbeddingProvider
from app.knowledge.models import DocumentChunk, KnowledgeResult


class ChromaAdapter:
    """Optional persistent Chroma adapter.

    If chromadb is installed, this adapter creates/uses the configured
    persistent collection. Otherwise callers should fall back to mock vector store.
    """

    def __init__(self, persist_dir: str, collection_name: str) -> None:
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.embedder = DeterministicEmbeddingProvider()
        self.client: Any | None = None
        self.collection: Any | None = None
        self.error: str | None = None
        self._initialize()

    def _initialize(self) -> None:
        try:
            import chromadb  # type: ignore
            self.client = chromadb.PersistentClient(path=self.persist_dir)
            self.collection = self.client.get_or_create_collection(name=self.collection_name)
        except Exception as exc:  # pragma: no cover - optional dependency
            self.error = str(exc)

    def is_available(self) -> bool:
        return self.collection is not None

    def count(self) -> int:
        if not self.is_available():
            return 0
        return int(self.collection.count())

    def upsert_chunks(self, chunks: list[DocumentChunk]) -> dict[str, Any]:
        if not self.is_available():
            raise RuntimeError(self.error or "Chroma is not available")

        ids = [chunk.chunk_id for chunk in chunks]
        documents = [chunk.text for chunk in chunks]
        embeddings = self.embedder.embed_many(documents)
        metadatas = [
            {
                "document_id": chunk.document_id,
                "document_name": chunk.document_name,
                "chunk_index": chunk.chunk_index,
                **chunk.metadata,
            }
            for chunk in chunks
        ]
        self.collection.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
        return {"upserted": len(chunks), "collection_count": self.count()}

    def search(self, query: str, top_k: int = 5) -> list[KnowledgeResult]:
        if not self.is_available():
            raise RuntimeError(self.error or "Chroma is not available")

        result = self.collection.query(
            query_embeddings=[self.embedder.embed(query)],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        items = []
        for i, doc in enumerate(documents):
            metadata = metadatas[i] or {}
            distance = distances[i] if i < len(distances) else 1.0
            score = max(0.0, 1.0 - float(distance))
            items.append(
                KnowledgeResult(
                    title=metadata.get("document_name", "Knowledge Document"),
                    source="chroma",
                    score=round(score, 4),
                    snippet=doc[:240],
                    metadata=metadata,
                )
            )
        return items
