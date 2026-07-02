from __future__ import annotations

import json
from app.ingestion.tigergraph_upsert import TigerGraphUpsertClient
from app.models.recommendations import RecommendationRecord


class TigerGraphRecommendationLinker:
    def __init__(self) -> None:
        self.upsert = TigerGraphUpsertClient()

    def upsert_recommendation(self, rec: RecommendationRecord) -> dict:
        payload = {
            "recommendation_id": rec.recommendation_id,
            "recommendation_type": rec.recommendation_type.value,
            "title": rec.title,
            "action_text": rec.action_text,
            "score": rec.score,
            "confidence": rec.confidence,
            "status": rec.status.value,
            "created_ts": rec.created_ts.isoformat(),
            "updated_ts": rec.updated_ts.isoformat(),
            "rationale": rec.rationale,
            "compliance_status": rec.compliance_status.value,
            "evidence_json": json.dumps(rec.evidence),
            "reasoning_steps_json": json.dumps(rec.reasoning_steps),
            "supporting_documents_json": json.dumps(rec.supporting_documents),
        }
        result = self.upsert.upsert_vertex("phx_dm_recommendation", rec.recommendation_id, payload)
        self.upsert.upsert_edge("phx_dm_recommendation_for_advisor", rec.recommendation_id, rec.entity_id, {})
        if rec.household_id:
            self.upsert.upsert_edge("phx_dm_recommendation_targets_household", rec.recommendation_id, rec.household_id, {})
        if rec.opportunity_id:
            self.upsert.upsert_edge("phx_dm_recommendation_based_on_opportunity", rec.recommendation_id, rec.opportunity_id, {})
        if rec.prediction_id:
            self.upsert.upsert_edge("phx_dm_recommendation_supported_by_prediction", rec.recommendation_id, rec.prediction_id, {})
        if rec.playbook_id:
            self.upsert.upsert_edge("phx_dm_recommendation_supported_by_playbook", rec.recommendation_id, rec.playbook_id, {})
        return result
