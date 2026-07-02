from __future__ import annotations

from app.ai.insights.insight_data_collector import InsightDataCollector
from app.ai.insights.insight_generation_engine import InsightGenerationEngine
from app.ai.insights.insight_repository import InsightRepository
from app.ai.insights.tigergraph_insight_linker import TigerGraphInsightLinker
from app.models.insights_coaching import InsightRequest, InsightDashboardPayload
from app.models.memory import ContextMemoryCreateRequest, MemoryScopeType, MemoryType
from app.services.memory_service import MemoryService


class InsightsCoachingService:
    def __init__(self) -> None:
        self.collector = InsightDataCollector()
        self.engine = InsightGenerationEngine()
        self.repo = InsightRepository()
        self.linker = TigerGraphInsightLinker()
        self.memory = MemoryService()

    def generate_dashboard_payload(self, request: InsightRequest) -> InsightDashboardPayload:
        data = self.collector.collect_for_scope(request.scope_type.value, request.scope_id, request.question)
        payload = self.engine.generate_payload(request, data)
        self.repo.save_payload(payload)

        if request.write_to_memory:
            scope_type = MemoryScopeType.ADVISOR if request.scope_type.value == "Advisor" else MemoryScopeType(request.scope_type.value)
            self.memory.create_memory(
                ContextMemoryCreateRequest(
                    memory_type=MemoryType.COACHING,
                    scope_type=scope_type,
                    scope_id=request.scope_id,
                    title=f"AI coaching insight for {request.scope_id}",
                    summary=payload.executive_summary,
                    facts={
                        "card_count": len(payload.cards),
                        "time_period": request.time_period,
                        "persona": request.persona,
                    },
                    confidence=0.86,
                    source="insights_coaching_service",
                ),
                write_to_graph=request.write_to_tigergraph,
            )

        if request.write_to_tigergraph:
            self.linker.upsert_payload(payload)

        return payload

    def list_cards(self, scope_id: str | None = None, limit: int = 100) -> list[dict]:
        return self.repo.list_cards(scope_id, limit)

    def counts(self) -> list[dict]:
        return self.repo.counts()
