from __future__ import annotations

from app.features.models import FeatureVector


class FeatureEngineeringService:
    def build_advisor_features(self, context: dict) -> FeatureVector:
        persona = context.get("persona", "Advisor")
        scope_id = context.get("scope_id", "ADV0001")
        multiplier = {"Advisor": 1.0, "MDW": 4.2, "DDW": 11.5, "Firm": 48.0}.get(persona, 1.0)
        features = {
            "revenue_ytd": 4_820_000 * multiplier,
            "revenue_growth_pct": 12.6,
            "managed_revenue_pct": 45.2,
            "household_count": 268 * min(multiplier, 3.0),
            "aum": 96_300_000 * multiplier,
            "nnm": 7_250_000 * multiplier,
            "ncf": 1_985_000 * multiplier,
            "meeting_cadence": 3.4,
            "crm_followups_open": 11,
            "agp_goal_attainment_pct": 72,
            "recommendation_accept_rate_pct": 64,
            "peer_gap_pct": -6.1,
        }
        return FeatureVector(entity_type="Advisor", entity_id=scope_id, features=features, metadata={"persona": persona, "period": context.get("period")})

    def build_household_features(self, household_id: str = "HH001") -> FeatureVector:
        features = {
            "aum": 18_200_000,
            "nnm": 1_120_000,
            "ncf": 310_000,
            "managed_asset_pct": 38,
            "cash_pct": 12,
            "meeting_count_l90": 2,
            "risk_score": 62,
            "opportunity_score": 91,
        }
        return FeatureVector(entity_type="Household", entity_id=household_id, features=features, metadata={"name": "Parker Family"})
