from __future__ import annotations

from typing import Protocol

from app.config.settings import get_settings


class EmbeddingClientError(RuntimeError):
    pass


class EmbeddingClient(Protocol):
    """Adapter interface for semantic text embeddings (Section 2 adapter pattern).

    Fully replaces the old sha256-seeded deterministic vectors — every knowledge
    embedding now comes from a real semantic model, local or Azure, selected by
    EMBEDDING_CLIENT_MODE. Nothing outside the implementations below may import
    sentence_transformers or the openai SDK for embeddings.
    """

    def embed(self, text: str) -> list[float]: ...

    def embed_many(self, texts: list[str]) -> list[list[float]]: ...

    def describe(self) -> dict: ...


class LocalEmbeddingClient:
    """sentence-transformers model, free and fully local — the default.

    Vectors are L2-normalized so cosine similarity in the vector store is the
    plain dot product; the same normalization the Azure embeddings API applies.
    """

    def __init__(self) -> None:
        settings = get_settings()
        # SDK import stays inside the class so mock/azure paths never load torch.
        from sentence_transformers import SentenceTransformer

        self.model_name = settings.local_embedding_model
        self._model = SentenceTransformer(self.model_name)
        self.dimensions = int(self._model.get_embedding_dimension())

    def embed(self, text: str) -> list[float]:
        return self.embed_many([text])[0]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(
            list(texts), normalize_embeddings=True, show_progress_bar=False
        )
        return [vector.tolist() for vector in vectors]

    def describe(self) -> dict:
        return {"mode": "local", "model": self.model_name, "dimensions": self.dimensions}


class AzureOpenAIEmbeddingClient:
    """Azure OpenAI embeddings — what runs at the client site. Same call sites,
    env-only cutover, mirroring RealLLMClient."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.azure_openai_endpoint or not settings.azure_openai_api_key:
            raise EmbeddingClientError(
                "EMBEDDING_CLIENT_MODE=azure requires AZURE_OPENAI_ENDPOINT and "
                "AZURE_OPENAI_API_KEY in .env"
            )
        from openai import AzureOpenAI  # imported here so nothing else depends on the SDK

        self._client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )
        self.deployment = settings.azure_openai_embedding_deployment

    def embed(self, text: str) -> list[float]:
        return self.embed_many([text])[0]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(model=self.deployment, input=list(texts))
        return [item.embedding for item in response.data]

    def describe(self) -> dict:
        return {"mode": "azure", "model": f"azure:{self.deployment}"}


_embedding_client: EmbeddingClient | None = None


def get_embedding_client() -> EmbeddingClient:
    """Select the EmbeddingClient per EMBEDDING_CLIENT_MODE (local | azure).

    Cached at module level — the local model load (~90MB) should happen once per
    process, not per request.
    """
    global _embedding_client
    if _embedding_client is not None:
        return _embedding_client
    mode = get_settings().embedding_client_mode.lower()
    if mode == "local":
        _embedding_client = LocalEmbeddingClient()
    elif mode == "azure":
        _embedding_client = AzureOpenAIEmbeddingClient()
    else:
        raise EmbeddingClientError(
            f"Unknown EMBEDDING_CLIENT_MODE '{mode}' (expected local | azure)"
        )
    return _embedding_client
