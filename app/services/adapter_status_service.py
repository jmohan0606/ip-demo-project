from __future__ import annotations

from app.config.settings import get_settings
from app.graph.client import get_graph_client
from app.llm.client import get_llm_client
from app.llm.embedding_client import get_embedding_client


class AdapterStatusService:
    """Reports which GraphClient/LLMClient/EmbeddingClient implementations are active (Section 2)."""

    def status(self) -> dict:
        settings = get_settings()
        graph_health = get_graph_client().health()
        llm = get_llm_client()
        return {
            "graph_client_mode": settings.graph_client_mode,
            "graph": graph_health,
            "llm_client_mode": settings.llm_client_mode,
            "llm": llm.describe(),
            "embedding_client_mode": settings.embedding_client_mode,
            "embedding": get_embedding_client().describe(),
            "anthropic_configured": bool(settings.anthropic_api_key),
            "azure_openai_configured": bool(settings.azure_openai_endpoint and settings.azure_openai_api_key),
        }
