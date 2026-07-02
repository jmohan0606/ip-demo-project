from __future__ import annotations

from app.models.opportunities import OpportunityType
from app.models.recommendations import RecommendationType


class PlaybookSelector:
    def select(self, opportunity_type: str) -> tuple[str, RecommendationType, str, list[str]]:
        if opportunity_type == OpportunityType.MANAGED_ACCOUNT_EXPANSION.value:
            return (
                "PB001",
                RecommendationType.MANAGED_ACCOUNT_REVIEW,
                "Schedule a managed account review meeting and document suitability, risk profile, liquidity needs and time horizon.",
                ["Managed Account Growth Playbook", "Compliance Recommendation Policy"],
            )
        if opportunity_type == OpportunityType.NNM_GROWTH.value:
            return (
                "PB002",
                RecommendationType.NNM_GROWTH_ACTION,
                "Review households with cash balances, rollover events, and recent liquidity activity to identify appropriate NNM growth actions.",
                ["NNM Growth Playbook", "Business Glossary"],
            )
        if opportunity_type == OpportunityType.AUM_RETENTION.value:
            return (
                "PB002",
                RecommendationType.AUM_RETENTION_ACTION,
                "Create a retention outreach list for households showing negative cash flow or reduced engagement.",
                ["NNM Growth Playbook", "Compliance Recommendation Policy"],
            )
        if opportunity_type == OpportunityType.AGP_GOAL_RECOVERY.value:
            return (
                "PB003",
                RecommendationType.AGP_COACHING_ACTION,
                "Create a weekly AGP coaching plan with MDW/DDW review and prioritized actions for off-track KPIs.",
                ["AGP Coaching Guide"],
            )
        if opportunity_type == OpportunityType.CRM_ENGAGEMENT_GAP.value:
            return (
                "PB001",
                RecommendationType.CRM_ENGAGEMENT_ACTION,
                "Increase CRM follow-up cadence and schedule review meetings for priority households.",
                ["Managed Account Growth Playbook", "AGP Coaching Guide"],
            )
        return (
            "PB001",
            RecommendationType.PEER_BENCHMARK_ACTION,
            "Review peer benchmark gaps and adopt best practices from similar high-performing advisors.",
            ["Managed Account Growth Playbook"],
        )
