from __future__ import annotations

import json
from app.ingestion.tigergraph_upsert import TigerGraphUpsertClient
from app.models.insights_coaching import InsightDashboardPayload


class TigerGraphInsightLinker:
    def __init__(self) -> None:
        self.upsert = TigerGraphUpsertClient()

    def upsert_payload(self, payload: InsightDashboardPayload) -> dict:
        linked = 0
        for card in payload.cards:
            trace_id = card.insight_id
            trace_payload = {
                "trace_id": trace_id,
                "trace_type": card.card_type.value,
                "conclusion": card.summary,
                "confidence": card.confidence,
                "reasoning_steps_json": json.dumps(card.reasoning_steps),
                "evidence_json": json.dumps([e.model_dump() for e in card.evidence]),
                "created_ts": payload.generated_at.isoformat(),
                "status": "Active",
            }
            self.upsert.upsert_vertex("phx_dm_reasoning_trace", trace_id, trace_payload)
            linked += 1
        return {"insight_traces_linked": linked}
