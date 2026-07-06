from __future__ import annotations

from app.config.settings import get_settings
from app.graph.client import get_graph_client
from app.graph.tier_log import get_tier_log
from app.llm.client import get_llm_client
from app.llm.embedding_client import get_embedding_client


class AdapterStatusService:
    """Reports which GraphClient/LLMClient/EmbeddingClient implementations are active (Section 2),
    including the Section-9.4 4-tier chain status + per-request tier usage log."""

    @staticmethod
    def _graph_tiers(client, settings) -> dict:
        if hasattr(client, "tier_status"):  # TieredGraphClient (auto/tiered/mcp/local_real/real)
            return client.tier_status()
        # direct mock/legacy client: single-tier chain, same shape for the Admin page
        return {
            "mode": settings.graph_client_mode,
            "chain": [{"tier": 4, "name": "mock", "instantiated": True, "cooldown_seconds_left": 0.0}],
            "cooldown_seconds": settings.graph_tier_cooldown_seconds,
            "usage": get_tier_log().summary(),
        }

    def status(self) -> dict:
        settings = get_settings()
        graph_client = get_graph_client()
        graph_health = graph_client.health()
        llm = get_llm_client()
        return {
            "graph_client_mode": settings.graph_client_mode,
            "graph": graph_health,
            "graph_tiers": self._graph_tiers(graph_client, settings),
            "llm_client_mode": settings.llm_client_mode,
            "llm": llm.describe(),
            "embedding_client_mode": settings.embedding_client_mode,
            "embedding": get_embedding_client().describe(),
            "model_client_mode": settings.model_client_mode,
            "model": self._model_tier(),
            "vector_client_mode": settings.vector_client_mode,
            "anthropic_configured": bool(settings.anthropic_api_key),
            "azure_openai_configured": bool(settings.azure_openai_endpoint and settings.azure_openai_api_key),
        }

    @staticmethod
    def _model_tier() -> dict:
        """Section 11.1: active ModelClient tier + which trained models are serving."""
        from app.ml import registry
        from app.ml.client import get_model_client

        described = get_model_client().describe()
        serving = [e["name"] for e in registry.list_entries() if e.get("quality_gate") == "passed"]
        return {**described, "registered": len(registry.list_entries()), "serving": serving}
