from __future__ import annotations

from app.feedback.feedback_repository import FeedbackLearningRepository
from app.feedback.learning_signal_engine import LearningSignalEngine
from app.feedback.reward_engine import FeedbackRewardEngine
from app.feedback.tigergraph_feedback_linker import TigerGraphFeedbackLinker
from app.models.feedback_learning import (
    FeedbackEventRecord,
    FeedbackSearchRequest,
    FeedbackSubmitRequest,
    FeedbackSubmitResult,
    OutcomeEventRecord,
    OutcomeType,
)
from app.models.memory import ContextMemoryCreateRequest, MemoryScopeType, MemoryType
from app.models.recommendations import RecommendationActionRequest, RecommendationStatus
from app.services.memory_service import MemoryService
from app.services.recommendation_service import RecommendationService
from app.shared.ids import timestamp_id


class FeedbackLearningService:
    def __init__(self) -> None:
        self.repo = FeedbackLearningRepository()
        self.reward_engine = FeedbackRewardEngine()
        self.signal_engine = LearningSignalEngine()
        self.linker = TigerGraphFeedbackLinker()
        self.recommendation_service = RecommendationService()
        self.memory_service = MemoryService()

    def submit_feedback(self, request: FeedbackSubmitRequest) -> FeedbackSubmitResult:
        reward = self.reward_engine.reward(request.action, request.outcome_type, request.outcome_value)

        feedback = FeedbackEventRecord(
            feedback_id=timestamp_id("fdbk"),
            recommendation_id=request.recommendation_id,
            actor=request.actor,
            action=request.action,
            reason=request.reason,
            modified_action_text=request.modified_action_text,
            reward_score=reward,
        )
        self.repo.save_feedback(feedback)

        outcome = None
        if request.outcome_type:
            outcome = OutcomeEventRecord(
                outcome_id=timestamp_id("out"),
                feedback_id=feedback.feedback_id,
                recommendation_id=request.recommendation_id,
                outcome_type=request.outcome_type,
                outcome_value=request.outcome_value or 0.0,
                outcome_summary=request.outcome_summary or f"{request.outcome_type.value} captured.",
            )
            self.repo.save_outcome(outcome)

        signal = self.signal_engine.create_signal(feedback, outcome)
        self.repo.save_learning_signal(signal)

        status_map = {
            "accept": RecommendationStatus.ACCEPTED,
            "reject": RecommendationStatus.REJECTED,
            "ignore": RecommendationStatus.IGNORED,
            "complete": RecommendationStatus.COMPLETED,
            "modify": RecommendationStatus.ACCEPTED,
        }
        updated_status = status_map.get(request.action.value, RecommendationStatus.GENERATED)
        self.recommendation_service.update_status(
            RecommendationActionRequest(
                recommendation_id=request.recommendation_id,
                status=updated_status,
                reason=request.reason,
            )
        )

        memory_updated = False
        rec = self.recommendation_service.repo.get_recommendation(request.recommendation_id)
        if rec:
            self.memory_service.create_memory(
                ContextMemoryCreateRequest(
                    memory_type=MemoryType.FEEDBACK,
                    scope_type=MemoryScopeType.ADVISOR,
                    scope_id=rec["entity_id"],
                    title=f"Feedback on recommendation {request.recommendation_id}",
                    summary=signal.signal_summary,
                    facts={
                        "recommendation_id": request.recommendation_id,
                        "feedback_id": feedback.feedback_id,
                        "action": feedback.action.value,
                        "reward_score": feedback.reward_score,
                        "ranking_weight_delta": signal.ranking_weight_delta,
                    },
                    confidence=0.90,
                    source="feedback_learning_service",
                ),
                write_to_graph=request.write_to_tigergraph,
            )
            memory_updated = True

        if request.write_to_tigergraph:
            self.linker.upsert_feedback(feedback)
            if outcome:
                self.linker.upsert_outcome(outcome)
            self.linker.upsert_learning_signal(signal)

        return FeedbackSubmitResult(
            feedback=feedback,
            outcome=outcome,
            learning_signal=signal,
            recommendation_status_updated=True,
            memory_updated=memory_updated,
        )

    def list_feedback(self, request: FeedbackSearchRequest) -> list[dict]:
        return self.repo.list_feedback(
            recommendation_id=request.recommendation_id,
            actor=request.actor.value if request.actor else None,
            action=request.action.value if request.action else None,
            limit=request.limit,
        )

    def list_learning_signals(self, limit: int = 100) -> list[dict]:
        return self.repo.list_learning_signals(limit)

    def counts(self) -> list[dict]:
        return self.repo.counts()
