from __future__ import annotations

from app.llm.embedding_client import get_embedding_client


class KnowledgeEmbeddingService:
    """Thin facade over the Section-2 EmbeddingClient adapter.

    Replaces the old ModelAdapterFactory path whose MockModelAdapter returned
    sha256-seeded random vectors (deterministic but not semantic).
    """

    def __init__(self) -> None:
        self.client = get_embedding_client()

    def embed(self, text: str) -> list[float]:
        return self.client.embed(text)

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return self.client.embed_many(texts)

    def describe(self) -> dict:
        return self.client.describe()
