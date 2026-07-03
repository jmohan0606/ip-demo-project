from __future__ import annotations

from datetime import date

from app.agp.service import SEVERITY_BANDS, _band
from app.features.snapshot_store import SnapshotStore
from app.graph.artifacts import upsert_edge, upsert_vertex, write_reasoning_trace
from app.graph.client import GraphClient, get_graph_client
from app.prediction.service import PredictionService

MODEL_VERSION = "v2.0"


def severity_score(intelligence: float, business_impact: float, time_sensitivity: float,
                   client_value: float, confidence: float) -> dict:
    """Spec Section 7 composition: 25% intelligence, 25% business impact,
    20% time sensitivity, 15% client importance, 15% confidence/risk evidence.
    All component scores preserved for explainability."""
    components = {
        "intelligence": round(intelligence, 1),
        "business_impact": round(business_impact, 1),
        "time_sensitivity": round(time_sensitivity, 1),
        "client_value": round(client_value, 1),
        "confidence_evidence": round(confidence, 1),
    }
    score = round(
        intelligence * 0.25 + business_impact * 0.25 + time_sensitivity * 0.20
        + client_value * 0.15 + confidence * 0.15,
        1,
    )
    return {"score": score, "severity": _band(score, SEVERITY_BANDS).capitalize(), "components": components}


class OpportunityDetectionService:
    """AI opportunity detection (distinct from CRM opportunities per CRM-003):
    rules over predictions + feature snapshot, severity per the spec's
    composition, persisted with full lineage."""

    def __init__(self, graph: GraphClient | None = None, as_of: date | None = None) -> None:
        self.graph = graph or get_graph_client()
        self.as_of = as_of or date(2026, 7, 3)
        self.snapshots = SnapshotStore()
        self.predictions = PredictionService(self.graph, as_of=self.as_of)

    def detect_for_advisor(self, advisor_id: str, persist: bool = True) -> dict:
        snapshot = self.snapshots.latest_for_entity("ADVISOR", advisor_id)
        if snapshot is None:
            self.predictions._snapshot(advisor_id)
            snapshot = self.snapshots.latest_for_entity("ADVISOR", advisor_id)
        f = snapshot["features"]
        preds = self.predictions.predict_advisor(advisor_id, persist=persist)["predictions"]
        by_type = {p.get("prediction_type"): p for p in preds if p.get("score") is not None}

        revenue_ltm = float(f.get("revenue_ltm") or 0)
        client_value = float(f.get("client_value_score") or 50)
        time_sensitivity = float(f.get("time_sensitivity_score") or 30)
        opportunities: list[dict] = []

        # Rule 1 — managed mix expansion: low managed ratio with a real book.
        managed_ratio = float(f.get("managed_revenue_ratio") or 0)
        if managed_ratio < 0.35 and revenue_ltm > 0:
            gap = 0.35 - managed_ratio
            impact = round(revenue_ltm * gap * 0.6, 2)
            sev = severity_score(
                intelligence=min(100, gap * 250),
                business_impact=min(100, impact / max(revenue_ltm, 1) * 300),
                time_sensitivity=time_sensitivity * 0.6,
                client_value=client_value,
                confidence=70,
            )
            opportunities.append({
                "opportunity_id": f"OPP_MANAGEDMIX_{advisor_id}_{MODEL_VERSION}",
                "opportunity_type": "ADVISOR_GROWTH", "category": "PRODUCT_MIX",
                "estimated_revenue_impact": impact,
                "impact_summary": (
                    f"Managed revenue is {managed_ratio:.1%} of the book vs a 35% benchmark; closing "
                    f"the gap is worth an estimated ${impact:,.0f} in advisory revenue."
                ),
                "derived_from_prediction": None,
                "evidence_features": ["managed_revenue_ratio", "revenue_ltm"],
                **sev,
            })

        # Rule 2 — revenue at risk: driven by the decline prediction.
        decline = by_type.get("REVENUE_DECLINE_RISK")
        if decline and decline["score"] >= 40:
            impact = float(f.get("revenue_at_risk_estimate") or revenue_ltm * decline["score"] / 400)
            sev = severity_score(
                intelligence=decline["score"],
                business_impact=min(100, impact / max(revenue_ltm, 1) * 400),
                time_sensitivity=time_sensitivity,
                client_value=client_value,
                confidence=decline["confidence"] * 100,
            )
            opportunities.append({
                "opportunity_id": f"OPP_REVRISK_{advisor_id}_{MODEL_VERSION}",
                "opportunity_type": "RETENTION", "category": "REVENUE_AT_RISK",
                "estimated_revenue_impact": round(impact, 2),
                "impact_summary": (
                    f"Revenue decline risk scored {decline['score']}/100; an estimated ${impact:,.0f} "
                    "of annualized revenue is exposed without intervention."
                ),
                "derived_from_prediction": decline["prediction_id"],
                "evidence_features": [c["feature"] for c in decline["contributions"]],
                **sev,
            })

        # Rule 3 — AGP milestone rescue: driven by the off-track prediction.
        agp = by_type.get("AGP_OFF_TRACK_RISK")
        if agp and agp.get("score") is not None and agp["score"] >= 40:
            impact = round(revenue_ltm * 0.12, 2)
            sev = severity_score(
                intelligence=agp["score"],
                business_impact=min(100, agp["score"] * 0.8),
                time_sensitivity=min(100, time_sensitivity * 1.4),
                client_value=client_value,
                confidence=agp["confidence"] * 100,
            )
            opportunities.append({
                "opportunity_id": f"OPP_AGPRESCUE_{advisor_id}_{MODEL_VERSION}",
                "opportunity_type": "AGP_MILESTONE", "category": "AGP_EXECUTION",
                "estimated_revenue_impact": impact,
                "impact_summary": (
                    f"AGP off-track risk scored {agp['score']}/100 for the current milestone; focused "
                    "CRM execution and coaching in the remaining window can recover attainment."
                ),
                "derived_from_prediction": agp["prediction_id"],
                "evidence_features": [c["feature"] for c in agp["contributions"]],
                **sev,
            })

        # Rule 4 — CRM pipeline acceleration: idle high-value open pipeline.
        pipeline_value = float(f.get("crm_pipeline_value") or 0)
        overdue = int(f.get("overdue_followup_count") or 0)
        if pipeline_value > 0 and overdue > 0:
            weighted = float(f.get("weighted_pipeline_value") or pipeline_value * 0.5)
            sev = severity_score(
                intelligence=min(100, overdue * 20),
                business_impact=min(100, weighted / max(revenue_ltm, 1) * 60),
                time_sensitivity=min(100, 40 + overdue * 15),
                client_value=client_value,
                confidence=75,
            )
            opportunities.append({
                "opportunity_id": f"OPP_PIPELINE_{advisor_id}_{MODEL_VERSION}",
                "opportunity_type": "CRM_EXECUTION", "category": "PIPELINE_ACCELERATION",
                "estimated_revenue_impact": round(weighted * 0.4, 2),
                "impact_summary": (
                    f"${pipeline_value:,.0f} of open CRM pipeline (${weighted:,.0f} weighted) with "
                    f"{overdue} overdue follow-ups; timely execution converts stalled work into revenue."
                ),
                "derived_from_prediction": None,
                "evidence_features": ["crm_pipeline_value", "weighted_pipeline_value", "overdue_followup_count"],
                **sev,
            })

        opportunities.sort(key=lambda o: -o["score"])
        if persist:
            for opp in opportunities:
                self._persist(opp, advisor_id, snapshot["snapshot_id"])
        return {"advisor_id": advisor_id, "opportunity_kind": "AI", "opportunities": opportunities,
                "feature_snapshot_id": snapshot["snapshot_id"]}

    def _persist(self, opp: dict, advisor_id: str, snapshot_id: str) -> None:
        record = {
            "opportunity_id": opp["opportunity_id"],
            "opportunity_type": opp["opportunity_type"],
            "category": opp["category"],
            "target_type": "ADVISOR",
            "target_id": advisor_id,
            "score": opp["score"],
            "severity": opp["severity"].upper(),
            "estimated_revenue_impact": opp["estimated_revenue_impact"],
            "impact_summary": opp["impact_summary"],
            "status": "OPEN",
            "generated_at": self.as_of.isoformat(),
        }
        upsert_vertex(self.graph, "phx_dm_opportunity", "opportunity_id", record)
        upsert_edge(self.graph, "phx_dm_opportunity_for_advisor", "phx_dm_opportunity", "phx_dm_advisor",
                    opp["opportunity_id"], advisor_id)
        upsert_edge(self.graph, "phx_dm_opportunity_uses_feature_snapshot", "phx_dm_opportunity",
                    "phx_dm_feature_snapshot", opp["opportunity_id"], snapshot_id)
        if opp.get("derived_from_prediction"):
            upsert_edge(self.graph, "phx_dm_opportunity_derived_from_prediction", "phx_dm_opportunity",
                        "phx_dm_prediction_result", opp["opportunity_id"], opp["derived_from_prediction"])
        write_reasoning_trace(
            self.graph,
            reasoning_id=f"REASON_{opp['opportunity_id']}",
            artifact_type="OPPORTUNITY",
            artifact_id=opp["opportunity_id"],
            steps=[
                "Load feature snapshot and active predictions",
                "Evaluate detection rule for this opportunity family",
                "Estimate revenue impact from the feature evidence",
                "Compose severity from intelligence/impact/time/client/confidence (25/25/20/15/15)",
            ],
            evidence={"severity_components": opp["components"], "evidence_features": opp["evidence_features"],
                      "derived_from_prediction": opp.get("derived_from_prediction")},
            feature_snapshot_id=snapshot_id,
            created_at=self.as_of.isoformat(),
        )
