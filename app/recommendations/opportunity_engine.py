from __future__ import annotations

from app.features import get_feature_runtime
from app.recommendations.models import Opportunity


class OpportunityEngine:
    def generate(self, context: dict) -> list[Opportunity]:
        feature_runtime = get_feature_runtime()
        vector = feature_runtime.get_or_create_advisor_vector(context)
        f = vector.features

        opportunities: list[Opportunity] = []

        managed_gap = max(0.0, 55.0 - f.get("managed_revenue_pct", 0))
        if managed_gap > 0:
            opportunities.append(Opportunity(
                opportunity_id="OPP-MANAGED-001",
                title="Managed Account Expansion",
                category="Managed Revenue",
                score=min(98, 70 + managed_gap * 1.4),
                impact=managed_gap * 38_000,
                priority="High" if managed_gap > 8 else "Medium",
                status="good",
                drivers=[
                    {"driver": "Managed revenue gap", "value": managed_gap},
                    {"driver": "Peer benchmark gap", "value": f.get("peer_gap_pct", 0)},
                ],
            ))

        if f.get("nnm", 0) < 1_000_000 or f.get("ncf", 0) < 500_000:
            opportunities.append(Opportunity(
                opportunity_id="OPP-NNM-002",
                title="NNM / NCF Recovery",
                category="Growth Recovery",
                score=89,
                impact=156_000,
                priority="High",
                status="warn",
                drivers=[
                    {"driver": "NNM below threshold", "value": f.get("nnm", 0)},
                    {"driver": "NCF below threshold", "value": f.get("ncf", 0)},
                ],
            ))

        if f.get("meeting_cadence", 0) < 4:
            opportunities.append(Opportunity(
                opportunity_id="OPP-MEETINGS-003",
                title="Increase Client Meeting Cadence",
                category="Client Engagement",
                score=82,
                impact=84_000,
                priority="Medium",
                status="warn",
                drivers=[
                    {"driver": "Meeting cadence", "value": f.get("meeting_cadence", 0)},
                    {"driver": "Open CRM follow-ups", "value": f.get("crm_followups_open", 0)},
                ],
            ))

        opportunities.sort(key=lambda item: item.score, reverse=True)
        return opportunities
