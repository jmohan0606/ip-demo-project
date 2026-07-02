from __future__ import annotations

from app.ai.adapters.adapter_factory import ModelAdapterFactory
from app.models.enums import AdapterProvider


class KnowledgeEmbeddingService:
    def __init__(self) -> None:
        self.adapter = ModelAdapterFactory.create(AdapterProvider.OPENAI)

    def embed(self, text: str) -> list[float]:
        return self.adapter.embed_text(text)
