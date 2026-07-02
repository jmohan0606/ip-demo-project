from __future__ import annotations

from app.recommendations.models import Opportunity, Recommendation


class RecommendationEngine:
    def generate(self, opportunities: list[Opportunity]) -> list[Recommendation]:
        recommendations: list[Recommendation] = []

        for opp in opportunities:
            if opp.opportunity_id.startswith("OPP-MANAGED"):
                recommendations.append(Recommendation(
                    recommendation_id="REC-MANAGED-001",
                    opportunity_id=opp.opportunity_id,
                    title="Schedule Managed Account Review",
                    action_type="Client Outreach",
                    priority=opp.priority,
                    confidence=min(0.96, opp.score / 100),
                    impact=opp.impact,
                    compliance_status="Passed",
                    reasoning=[
                        "Managed revenue penetration is below target benchmark.",
                        "Household opportunity score indicates high suitability.",
                        "Playbook evidence supports advisory review conversation.",
                    ],
                    next_steps=[
                        "Identify 15 high-potential households.",
                        "Schedule portfolio review meetings.",
                        "Document suitability and client objective alignment.",
                    ],
                ))
            elif opp.opportunity_id.startswith("OPP-NNM"):
                recommendations.append(Recommendation(
                    recommendation_id="REC-NNM-002",
                    opportunity_id=opp.opportunity_id,
                    title="Launch NNM Recovery Sequence",
                    action_type="Retention / Recovery",
                    priority="High",
                    confidence=0.86,
                    impact=opp.impact,
                    compliance_status="Review Required",
                    reasoning=[
                        "NNM/NCF indicators show recovery opportunity.",
                        "Recent outflow pattern requires advisor follow-up.",
                    ],
                    next_steps=[
                        "Review households with negative NCF.",
                        "Confirm liquidity drivers.",
                        "Schedule retention and planning calls.",
                    ],
                ))
            else:
                recommendations.append(Recommendation(
                    recommendation_id="REC-MEETING-003",
                    opportunity_id=opp.opportunity_id,
                    title="Increase Client Meeting Cadence",
                    action_type="Advisor Coaching",
                    priority=opp.priority,
                    confidence=0.79,
                    impact=opp.impact,
                    compliance_status="Passed",
                    reasoning=[
                        "Meeting cadence is below peer range.",
                        "CRM follow-ups show open engagement opportunities.",
                    ],
                    next_steps=[
                        "Prioritize top 25 households.",
                        "Set weekly follow-up plan.",
                        "Track conversion to revenue opportunity.",
                    ],
                ))

        return recommendations
