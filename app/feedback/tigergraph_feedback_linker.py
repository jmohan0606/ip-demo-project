from __future__ import annotations

from app.ingestion.tigergraph_upsert import TigerGraphUpsertClient
from app.models.feedback_learning import FeedbackEventRecord, LearningSignalRecord, OutcomeEventRecord


class TigerGraphFeedbackLinker:
    def __init__(self) -> None:
        self.upsert = TigerGraphUpsertClient()

    def upsert_feedback(self, feedback: FeedbackEventRecord) -> dict:
        payload = {
            "feedback_id": feedback.feedback_id,
            "feedback_action": feedback.action.value,
            "feedback_reason": feedback.reason or "",
            "reward_score": feedback.reward_score,
            "created_ts": feedback.created_ts.isoformat(),
            "status": feedback.status,
            "actor": feedback.actor.value,
            "modified_action_text": feedback.modified_action_text or "",
        }
        result = self.upsert.upsert_vertex("phx_dm_feedback_event", feedback.feedback_id, payload)
        self.upsert.upsert_edge("phx_dm_feedback_for_recommendation", feedback.feedback_id, feedback.recommendation_id, {})
        return result

    def upsert_outcome(self, outcome: OutcomeEventRecord) -> dict:
        payload = {
            "outcome_id": outcome.outcome_id,
            "outcome_type": outcome.outcome_type.value,
            "outcome_value": outcome.outcome_value,
            "outcome_summary": outcome.outcome_summary,
            "created_ts": outcome.created_ts.isoformat(),
            "status": outcome.status,
        }
        result = self.upsert.upsert_vertex("phx_dm_outcome_event", outcome.outcome_id, payload)
        self.upsert.upsert_edge("phx_dm_outcome_for_feedback", outcome.outcome_id, outcome.feedback_id, {})
        return result

    def upsert_learning_signal(self, signal: LearningSignalRecord) -> dict:
        payload = {
            "learning_signal_id": signal.learning_signal_id,
            "signal_type": signal.signal_type.value,
            "signal_value": signal.signal_value,
            "signal_summary": signal.signal_summary,
            "created_ts": signal.created_ts.isoformat(),
            "status": signal.status,
            "ranking_weight_delta": signal.ranking_weight_delta,
        }
        result = self.upsert.upsert_vertex("phx_dm_learning_signal", signal.learning_signal_id, payload)
        if signal.outcome_id:
            self.upsert.upsert_edge("phx_dm_learning_from_outcome", signal.learning_signal_id, signal.outcome_id, {})
        self.upsert.upsert_edge("phx_dm_learning_updates_recommendation", signal.learning_signal_id, signal.recommendation_id, {})
        return result
