from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field

from app.models.embeddings import EmbeddingBuildRequest, EmbeddingEntityType
from app.models.features import FeatureMaterializationRequest
from app.models.feedback_learning import FeedbackAction, FeedbackActor, FeedbackSubmitRequest, OutcomeType
from app.models.insights_coaching import InsightRequest, InsightScopeType
from app.models.predictions import PredictionRunRequest
from app.models.recommendations import RecommendationRunRequest, RecommendationSearchRequest
from app.services.embedding_similarity_service import EmbeddingSimilarityService
from app.services.feature_store_service import FeatureStoreService
from app.services.feedback_learning_service import FeedbackLearningService
from app.services.insights_coaching_service import InsightsCoachingService
from app.services.knowledge_management_service import KnowledgeManagementService
from app.services.prediction_service import PredictionService
from app.services.recommendation_service import RecommendationService


class DemoStepResult(BaseModel):
    step_name: str
    status: str
    message: str
    records: int = 0
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime = Field(default_factory=datetime.utcnow)


class DemoRunResult(BaseModel):
    run_id: str
    status: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime = Field(default_factory=datetime.utcnow)
    steps: list[DemoStepResult] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)


class EndToEndDemoOrchestrator:
    def run_full_local_demo(self, advisor_id: str = "ADV0001") -> DemoRunResult:
        result = DemoRunResult(run_id=f"demo_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}", status="running")

        def add(step_name: str, status: str, message: str, records: int = 0) -> None:
            result.steps.append(DemoStepResult(step_name=step_name, status=status, message=message, records=records))

        try:
            knowledge = KnowledgeManagementService().ingest_sample_knowledge()
            add("Knowledge ingestion", "completed", "Sample knowledge documents indexed.", len(knowledge))

            features = FeatureStoreService().materialize(FeatureMaterializationRequest())
            add("Feature materialization", "completed", "Feature vectors materialized.", sum(x.records_materialized for x in features))

            embeddings = EmbeddingSimilarityService().build_embeddings_and_similarity(
                EmbeddingBuildRequest(
                    entity_types=[EmbeddingEntityType.ADVISOR, EmbeddingEntityType.HOUSEHOLD],
                    top_k_similarity=3,
                    write_to_tigergraph=False,
                )
            )
            add("Graph embeddings and similarity", "completed", embeddings.message, embeddings.embeddings_created)

            predictions = PredictionService().run_predictions(PredictionRunRequest(write_to_tigergraph=False))
            add("Predictions", "completed", predictions.message, predictions.predictions_created)

            recommendations = RecommendationService().run_recommendations(
                RecommendationRunRequest(entity_id=advisor_id, write_to_tigergraph=False, limit=50)
            )
            add("Opportunities and recommendations", "completed", recommendations.message, recommendations.recommendations_created)

            recs = RecommendationService().list_recommendations(RecommendationSearchRequest(entity_id=advisor_id, limit=1))
            feedback_records = 0
            if recs:
                feedback = FeedbackLearningService().submit_feedback(
                    FeedbackSubmitRequest(
                        recommendation_id=recs[0]["recommendation_id"],
                        actor=FeedbackActor.ADVISOR,
                        action=FeedbackAction.ACCEPT,
                        reason="Accepted during end-to-end demo validation.",
                        outcome_type=OutcomeType.REVENUE_IMPACT,
                        outcome_value=25000,
                        outcome_summary="Simulated revenue impact from accepted recommendation.",
                        write_to_tigergraph=False,
                    )
                )
                feedback_records = 1 if feedback.feedback.feedback_id else 0
            add("Feedback learning", "completed", "Feedback event, outcome and learning signal generated.", feedback_records)

            insights = InsightsCoachingService().generate_dashboard_payload(
                InsightRequest(
                    scope_type=InsightScopeType.ADVISOR,
                    scope_id=advisor_id,
                    persona="Advisor",
                    time_period="YTD",
                    question="Generate final demo insight and coaching plan.",
                    write_to_tigergraph=False,
                    write_to_memory=True,
                )
            )
            add("AI insights and coaching", "completed", "Insight cards and coaching plan generated.", len(insights.cards))

            result.status = "completed"
            result.summary = {
                "advisor_id": advisor_id,
                "knowledge_documents": len(knowledge),
                "feature_records": sum(x.records_materialized for x in features),
                "embedding_records": embeddings.embeddings_created,
                "similarity_matches": embeddings.similarity_matches_created,
                "predictions": predictions.predictions_created,
                "recommendations": recommendations.recommendations_created,
                "feedback_records": feedback_records,
                "insight_cards": len(insights.cards),
            }
        except Exception as exc:
            add("Demo orchestration", "failed", str(exc), 0)
            result.status = "failed"

        result.completed_at = datetime.utcnow()
        return result
