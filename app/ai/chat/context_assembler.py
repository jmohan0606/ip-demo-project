from __future__ import annotations

from app.models.ai_chat import ChatContextItem, ChatContextSource, ChatRequest
from app.models.insights_coaching import InsightRequest, InsightScopeType
from app.models.knowledge import KnowledgeSearchRequest
from app.models.memory import MemoryRetrievalRequest, MemoryScopeType
from app.models.predictions import PredictionSearchRequest
from app.opportunities.service import OpportunityDetectionService
from app.recommendations.service import RecommendationService as RecommendationPipelineService
from app.services.context_service import ContextService
from app.services.insights_coaching_service import InsightsCoachingService
from app.services.knowledge_management_service import KnowledgeManagementService
from app.services.prediction_service import PredictionService


class ChatContextAssembler:
    def __init__(self) -> None:
        self.context_service = ContextService()
        self.knowledge_service = KnowledgeManagementService()
        self.insight_service = InsightsCoachingService()
        self.prediction_service = PredictionService()
        self.opportunity_service = OpportunityDetectionService()
        self.recommendation_service = RecommendationPipelineService()

    def assemble(self, request: ChatRequest) -> list[ChatContextItem]:
        items: list[ChatContextItem] = []

        if request.include_memory:
            try:
                memory_scope = MemoryScopeType.ADVISOR if request.scope_type.value == "Advisor" else MemoryScopeType(request.scope_type.value)
                package = self.context_service.build_context_package(
                    MemoryRetrievalRequest(
                        scope_type=memory_scope,
                        scope_id=request.scope_id,
                        query=request.question,
                        limit=8,
                    )
                )
                items.append(ChatContextItem(
                    source=ChatContextSource.CONTEXT_MEMORY,
                    title="Context Memory Summary",
                    content=package.context_summary,
                    score=float(package.evidence_count),
                    metadata={"evidence_count": package.evidence_count},
                ))
            except Exception as exc:
                items.append(ChatContextItem(
                    source=ChatContextSource.CONTEXT_MEMORY,
                    title="Context Memory Unavailable",
                    content=str(exc),
                    score=0,
                ))

        if request.include_knowledge:
            try:
                search = self.knowledge_service.search(
                    KnowledgeSearchRequest(query=request.question, top_k=4)
                )
                for result in search.results:
                    items.append(ChatContextItem(
                        source=ChatContextSource.KNOWLEDGE_RAG,
                        title=result.document_name,
                        content=result.chunk_text,
                        score=result.score,
                        metadata=result.metadata,
                    ))
            except Exception as exc:
                items.append(ChatContextItem(
                    source=ChatContextSource.KNOWLEDGE_RAG,
                    title="Knowledge Search Unavailable",
                    content=str(exc),
                    score=0,
                ))

        entity_id = request.scope_id if request.scope_type.value == "Advisor" else None

        if request.include_insights:
            try:
                payload = self.insight_service.generate_dashboard_payload(
                    InsightRequest(
                        scope_type=InsightScopeType(request.scope_type.value),
                        scope_id=request.scope_id,
                        persona=request.persona.value,
                        question=request.question,
                        write_to_tigergraph=False,
                        write_to_memory=False,
                    )
                )
                items.append(ChatContextItem(
                    source=ChatContextSource.INSIGHTS,
                    title="Generated Insight Summary",
                    content=payload.executive_summary,
                    score=len(payload.cards),
                    metadata={"card_count": len(payload.cards)},
                ))
            except Exception as exc:
                items.append(ChatContextItem(
                    source=ChatContextSource.INSIGHTS,
                    title="Insights Unavailable",
                    content=str(exc),
                    score=0,
                ))

        try:
            predictions = self.prediction_service.list_predictions(
                PredictionSearchRequest(entity_id=entity_id, limit=5)
            )
            for p in predictions[:5]:
                items.append(ChatContextItem(
                    source=ChatContextSource.PREDICTIONS,
                    title=p.get("prediction_type", "Prediction"),
                    content=p.get("explanation", ""),
                    score=p.get("score"),
                    metadata=p,
                ))
        except Exception:
            pass

        if entity_id:
            try:
                # Real Phase-8 detection (severity-composed opportunities with lineage) — the
                # same OpportunityDetectionService the /opportunities router and agent toolbox
                # use. Replaces the legacy repo-backed OpportunityService, which read an
                # unpopulated store and returned zero opportunities for chat grounding.
                opportunities = self.opportunity_service.detect_for_advisor(entity_id)["opportunities"]
                for o in opportunities[:5]:
                    items.append(ChatContextItem(
                        source=ChatContextSource.OPPORTUNITIES,
                        title=o.get("opportunity_type") or "Opportunity",
                        content=o.get("impact_summary", ""),
                        score=o.get("score"),
                        metadata=o,
                    ))
            except Exception:
                pass

        if entity_id:
            try:
                # Real Phase-8/9 learning-weighted next-best-actions (same pipeline the
                # /recommendations router uses). Replaces the legacy repo-backed
                # list_recommendations, which read an unpopulated store and returned zero recs.
                recommendations = self.recommendation_service.generate_for_advisor(entity_id)["recommendations"]
                for r in recommendations[:5]:
                    items.append(ChatContextItem(
                        source=ChatContextSource.RECOMMENDATIONS,
                        title=r.get("title", "Recommendation"),
                        content=r.get("action_text", ""),
                        score=r.get("priority_score", r.get("score")),
                        metadata=r,
                    ))
            except Exception:
                pass

        return items
