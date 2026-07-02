from __future__ import annotations

import json
from app.ingestion.tigergraph_upsert import TigerGraphUpsertClient
from app.models.opportunities import OpportunityRecord


class TigerGraphOpportunityLinker:
    def __init__(self) -> None:
        self.upsert = TigerGraphUpsertClient()

    def upsert_opportunity(self, opp: OpportunityRecord) -> dict:
        payload = {
            "opportunity_id": opp.opportunity_id,
            "opportunity_type": opp.opportunity_type.value,
            "title": opp.title,
            "description": opp.description,
            "score": opp.score,
            "priority": opp.priority.value,
            "status": opp.status.value,
            "created_ts": opp.created_ts.isoformat(),
            "evidence_json": json.dumps(opp.evidence),
            "reasoning_steps_json": json.dumps(opp.reasoning_steps),
        }
        result = self.upsert.upsert_vertex("phx_dm_opportunity", opp.opportunity_id, payload)
        self.upsert.upsert_edge("phx_dm_opportunity_for_advisor", opp.opportunity_id, opp.entity_id, {})
        if opp.household_id:
            self.upsert.upsert_edge("phx_dm_opportunity_for_household", opp.opportunity_id, opp.household_id, {})
        if opp.prediction_id:
            self.upsert.upsert_edge("phx_dm_opportunity_supported_by_prediction", opp.opportunity_id, opp.prediction_id, {})
        return result
