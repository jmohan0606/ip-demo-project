from __future__ import annotations

from app.features.models import FeatureVector, PredictionResult


class PredictionRuntime:
    """Deterministic local prediction runtime.

    This is intentionally transparent and explainable. It can later be replaced
    with sklearn/XGBoost/GNN model scoring without changing API contracts.
    """

    def forecast_revenue(self, vector: FeatureVector, scenario: dict | None = None) -> PredictionResult:
        f = vector.features
        scenario = scenario or {}
        baseline = f.get("revenue_ytd", 0.0)
        lift_pct = (
            f.get("revenue_growth_pct", 0) * 0.18
            + max(f.get("managed_revenue_pct", 0) - 40, 0) * 0.22
            + scenario.get("meeting_increase_pct", 0) * 0.12
            + scenario.get("managed_revenue_shift_pct", 0) * 0.31
            + scenario.get("prospect_conversion_increase_pct", 0) * 0.18
        )
        predicted = baseline * (1 + lift_pct / 100)
        return PredictionResult(
            target="revenue",
            baseline=baseline,
            predicted=predicted,
            confidence=0.86,
            scenario_delta=predicted - baseline,
            drivers=[
                {"driver": "Revenue growth trend", "contribution": round(f.get("revenue_growth_pct", 0) * 0.18, 2), "direction": "positive"},
                {"driver": "Managed revenue mix", "contribution": round(max(f.get("managed_revenue_pct", 0) - 40, 0) * 0.22, 2), "direction": "positive"},
                {"driver": "Meeting cadence increase", "contribution": round(scenario.get("meeting_increase_pct", 0) * 0.12, 2), "direction": "positive"},
            ],
        )

    def forecast_nnm(self, vector: FeatureVector, scenario: dict | None = None) -> PredictionResult:
        f = vector.features
        scenario = scenario or {}
        baseline = f.get("nnm", 0.0)
        lift_pct = scenario.get("nnm_increase_pct", 0) + max(f.get("recommendation_accept_rate_pct", 0) - 50, 0) * 0.08
        predicted = baseline * (1 + lift_pct / 100)
        return PredictionResult(
            target="nnm",
            baseline=baseline,
            predicted=predicted,
            confidence=0.79,
            scenario_delta=predicted - baseline,
            drivers=[
                {"driver": "NNM scenario improvement", "contribution": scenario.get("nnm_increase_pct", 0), "direction": "positive"},
                {"driver": "Recommendation accept rate", "contribution": round(max(f.get("recommendation_accept_rate_pct", 0) - 50, 0) * 0.08, 2), "direction": "positive"},
            ],
        )

    def forecast_agp_goal(self, vector: FeatureVector, scenario: dict | None = None) -> PredictionResult:
        f = vector.features
        scenario = scenario or {}
        baseline = f.get("agp_goal_attainment_pct", 0.0)
        lift = scenario.get("meeting_increase_pct", 0) * 0.20 + scenario.get("prospect_conversion_increase_pct", 0) * 0.15
        predicted = min(100.0, baseline + lift)
        return PredictionResult(
            target="agp_goal",
            baseline=baseline,
            predicted=predicted,
            confidence=0.82,
            scenario_delta=predicted - baseline,
            drivers=[
                {"driver": "Meeting cadence", "contribution": round(scenario.get("meeting_increase_pct", 0) * 0.20, 2), "direction": "positive"},
                {"driver": "Prospect conversion", "contribution": round(scenario.get("prospect_conversion_increase_pct", 0) * 0.15, 2), "direction": "positive"},
            ],
        )
