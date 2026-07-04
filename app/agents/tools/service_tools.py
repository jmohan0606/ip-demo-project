from __future__ import annotations
from typing import Any
from app.models.embeddings import EmbeddingBuildRequest, EmbeddingEntityType
from app.models.features import FeatureMaterializationRequest
from app.models.insights_coaching import InsightRequest, InsightScopeType
from app.models.knowledge import KnowledgeSearchRequest
from app.models.memory import MemoryRetrievalRequest, MemoryScopeType
from app.models.opportunities import OpportunityRunRequest, OpportunitySearchRequest
from app.models.predictions import PredictionRunRequest, PredictionSearchRequest
from app.models.recommendations import RecommendationRunRequest, RecommendationSearchRequest
from app.services.context_service import ContextService
from app.services.embedding_similarity_service import EmbeddingSimilarityService
from app.services.feature_store_service import FeatureStoreService
from app.services.graph_access_service import GraphAccessService
from app.services.insights_coaching_service import InsightsCoachingService
from app.services.knowledge_management_service import KnowledgeManagementService
from app.services.opportunity_service import OpportunityService
from app.services.prediction_service import PredictionService
from app.services.recommendation_service import RecommendationService

class AgentToolbox:
    def graph_health(self) -> dict[str, Any]: return GraphAccessService().health()
    def graph_query_advisor_evidence(self, advisor_id: str) -> dict[str, Any]:
        return GraphAccessService().run_installed_query('phx_dm_getInsightEvidenceForAdvisor', {'advisorId': advisor_id, 'advisor_id': advisor_id})
    def retrieve_context(self, scope_type: str, scope_id: str, question: str) -> dict[str, Any]:
        scope = MemoryScopeType.ADVISOR if scope_type == 'Advisor' else MemoryScopeType(scope_type)
        return ContextService().build_context_package(MemoryRetrievalRequest(scope_type=scope, scope_id=scope_id, query=question, limit=10)).model_dump()
    def search_knowledge(self, question: str) -> dict[str, Any]:
        return KnowledgeManagementService().search(KnowledgeSearchRequest(query=question, top_k=5)).model_dump()
    def ask_knowledge(self, question: str, top_k: int = 5) -> dict[str, Any]:
        # Full RAG: retrieval + grounded generation with cited sources.
        from app.knowledge.rag_service import RagGenerationService
        return RagGenerationService().answer(question, top_k=top_k)
    def materialize_features(self) -> list[dict[str, Any]]:
        return [r.model_dump() for r in FeatureStoreService().materialize(FeatureMaterializationRequest())]
    def build_embeddings(self) -> dict[str, Any]:
        return EmbeddingSimilarityService().build_embeddings_and_similarity(EmbeddingBuildRequest(entity_types=[EmbeddingEntityType.ADVISOR, EmbeddingEntityType.HOUSEHOLD], top_k_similarity=3, write_to_tigergraph=False)).model_dump()
    def run_predictions(self, entity_id: str | None = None) -> list[dict[str, Any]]:
        # New Phase-7 pipeline: transparent scored predictions with contributions.
        if not entity_id:
            return []
        from app.prediction.service import PredictionService as PipelinePredictionService
        preds = PipelinePredictionService().predict_advisor(entity_id)["predictions"]
        return [p for p in preds if p.get("score") is not None]

    def run_opportunities(self, entity_id: str | None = None) -> list[dict[str, Any]]:
        # New Phase-8 detection: severity-composed AI opportunities with lineage.
        if not entity_id:
            return []
        from app.opportunities.service import OpportunityDetectionService
        return OpportunityDetectionService().detect_for_advisor(entity_id)["opportunities"]

    def run_recommendations(self, entity_id: str | None = None) -> list[dict[str, Any]]:
        # New Phase-8/9 pipeline: learning-weighted next-best-actions. Map priority_score
        # onto the 'score' key the agent nodes read.
        if not entity_id:
            return []
        from app.recommendations.service import RecommendationService as PipelineRecommendationService
        recs = PipelineRecommendationService().generate_for_advisor(entity_id)["recommendations"]
        for rec in recs:
            rec.setdefault("score", rec.get("priority_score"))
        return recs

    def generate_insights(self, scope_type: str, scope_id: str, persona: str, time_period: str, question: str) -> dict[str, Any]:
        return InsightsCoachingService().generate_dashboard_payload(InsightRequest(scope_type=InsightScopeType(scope_type), scope_id=scope_id, persona=persona, time_period=time_period, question=question, write_to_tigergraph=False, write_to_memory=True)).model_dump()
