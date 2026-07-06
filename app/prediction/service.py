from __future__ import annotations

from datetime import date

from app.agp.service import SEVERITY_BANDS, AgpService, _band
from app.features.engineering import FeatureEngineeringService
from app.features.snapshot_store import SnapshotStore
from app.graph.artifacts import upsert_edge, upsert_vertex, write_reasoning_trace
from app.graph.client import GraphClient, get_graph_client
from app.ml.client import ModelUnavailableError, get_model_client

MODEL_VERSION = "v2.0"


def _risk_band(score: float) -> str:
    return _band(score, SEVERITY_BANDS).upper()


class PredictionService:
    """Prediction engine per Prediction_Types (spec Section 11): transparent
    deterministic scoring over the feature snapshot, producing score,
    confidence, per-feature contributions and a persisted reasoning trace."""

    def __init__(self, graph: GraphClient | None = None, as_of: date | None = None) -> None:
        self.graph = graph or get_graph_client()
        self.as_of = as_of or date(2026, 7, 3)
        self.snapshots = SnapshotStore()

    def _snapshot(self, advisor_id: str) -> dict:
        engine = FeatureEngineeringService(self.graph, as_of=self.as_of)
        snapshot = self.snapshots.latest_for_entity("ADVISOR", advisor_id)
        if snapshot is None:
            computed = engine.compute_advisor_snapshot(advisor_id)
            engine.persist_snapshot(computed)
            snapshot = self.snapshots.latest_for_entity("ADVISOR", advisor_id)
        else:
            engine.ensure_graph_artifact(snapshot)
        return snapshot

    @staticmethod
    def _confidence(features: dict, used: list[str]) -> float:
        present = sum(1 for name in used if features.get(name) is not None)
        return round(0.5 + 0.45 * present / len(used), 2) if used else 0.5

    @staticmethod
    def _methodology(ptype: str, contributions: list[dict], score: float) -> dict:
        """The derivation detail (CLAUDE.md 9.5): the pipeline, the model/formula and
        the per-feature attribution. Honest — these are transparent additive scorecards
        (real code, per-feature weights). When a trained XGBoost model passes its registry
        quality gate for a prediction type (Section 11.1), the live path serves that model
        instead (with real TreeSHAP attribution) and this methodology is patched with its
        details; otherwise the scorecard below serves and served_by='scorecard'."""
        used = [c["feature"] for c in contributions]
        return {
            "model_name": "iPerform Risk Scorecard",
            "model_family": "Additive weighted scorecard · transparent per-feature attribution",
            "model_version": MODEL_VERSION,
            "trained_alternative": "XGBoost model (served when its held-out quality gate is met; Section 11.1)",
            "pipeline": [
                "Compute the advisor's Phase-5 feature snapshot from graph facts",
                f"Select the {len(used)} risk-driver features for {ptype.replace('_', ' ').title()}",
                "Score each feature by its documented weight → points (clamped 0–100)",
                "Sum the points and clamp the total to a 0–100 risk score",
                "Map score → risk band; derive confidence from feature coverage",
                "Persist the score with a full reasoning trace (feature → points → score)",
            ],
            "features_used": used,
            "score_formula": "risk_score = clamp(Σ feature_points, 0, 100)  ·  band = severity_band(risk_score)",
            "computed_score": score,
        }

    def _result_from_model(self, advisor_id: str, ptype: str, id_prefix: str,
                           snapshot: dict, ms: dict, horizon_days: int) -> dict:
        """Assemble the standard result dict from a real ModelScore. The methodology is the
        scorecard base patched by the model's methodology_patch + served_by, so the frontend
        'how this was derived' section gets strictly deeper, not different."""
        score = ms["score"]
        methodology = {
            **self._methodology(ptype, ms["contributions"], score),
            **ms["methodology_patch"],
            "served_by": ms["served_by"],
        }
        return {
            "prediction_id": f"{id_prefix}_{advisor_id}_{MODEL_VERSION}",
            "prediction_type": ptype,
            "target_type": "ADVISOR",
            "target_id": advisor_id,
            "score": score,
            "risk_band": _risk_band(score),
            "severity": _risk_band(score),
            "confidence": ms["confidence"],
            "horizon_days": horizon_days,
            "contributions": ms["contributions"],
            "feature_snapshot_id": snapshot["snapshot_id"],
            "explanation": ms.get("explanation", f"Trained model score {score}/100."),
            "methodology": methodology,
        }

    # -- Prediction type 1: Revenue Decline Risk --

    def predict_revenue_decline(self, advisor_id: str, persist: bool = True) -> dict:
        """Real-model tier first (Section 11.1 §2); falls back to the deterministic
        scorecard when no trained model passes its registry quality gate for this type."""
        snapshot = self._snapshot(advisor_id)
        try:
            ms = get_model_client().score_risk(
                "REVENUE_DECLINE_RISK", "ADVISOR", advisor_id, snapshot["features"])
            result = self._result_from_model(
                advisor_id, "REVENUE_DECLINE_RISK", "PRED_REVDECL", snapshot, ms, 180)
        except ModelUnavailableError as exc:
            result = self._revenue_decline_scorecard(advisor_id, snapshot, fallback_reason=str(exc))
        if persist:
            self._persist(result)
        return result

    def _revenue_decline_scorecard(self, advisor_id: str, snapshot: dict,
                                   fallback_reason: str | None = None) -> dict:
        f = snapshot["features"]
        contributions = []

        def contribute(name: str, points: float, why: str) -> float:
            points = round(max(0.0, min(points, 100.0)), 1)
            contributions.append({"feature": name, "value": f.get(name), "points": points, "why": why})
            return points

        growth = float(f.get("revenue_growth_3m_pct") or 0)
        ncf = float(f.get("ncf_3m") or 0)
        diversification = float(f.get("product_diversification_score") or 0)
        peer_gap = float(f.get("peer_revenue_gap_pct") or 0)
        days_idle = f.get("days_since_last_client_activity")

        score = 0.0
        score += contribute("revenue_growth_3m_pct", max(0, -growth) * 1.2, "negative trailing growth raises risk")
        score += contribute("ncf_3m", 25 if ncf < 0 else 0, "net cash outflow signals attrition")
        score += contribute("product_diversification_score", (0.5 - diversification) * 40 if diversification < 0.5 else 0,
                            "concentration in few products amplifies decline scenarios")
        score += contribute("peer_revenue_gap_pct", min(25, max(0, -peer_gap) * 0.4), "trailing the market peer cohort")
        score += contribute("days_since_last_client_activity",
                            min(15, max(0, (days_idle or 0) - 14) * 0.75), "stale client engagement")
        score = round(min(100.0, score), 1)

        used = [c["feature"] for c in contributions]
        methodology = self._methodology("REVENUE_DECLINE_RISK", contributions, score)
        methodology["served_by"] = "scorecard"
        if fallback_reason:
            methodology["fallback_reason"] = fallback_reason
        return {
            "prediction_id": f"PRED_REVDECL_{advisor_id}_{MODEL_VERSION}",
            "prediction_type": "REVENUE_DECLINE_RISK",
            "target_type": "ADVISOR",
            "target_id": advisor_id,
            "score": score,
            "risk_band": _risk_band(score),
            "severity": _risk_band(score),
            "confidence": self._confidence(f, used),
            "horizon_days": 90,
            "contributions": contributions,
            "feature_snapshot_id": snapshot["snapshot_id"],
            "explanation": (
                f"Deterministic weighted score {score}/100 from revenue trend ({growth:+.1f}% 3m), "
                f"net cash flow ({ncf:,.0f}), diversification ({diversification:.2f}), "
                f"peer gap ({peer_gap:+.1f}%) and engagement recency."
            ),
            "methodology": methodology,
        }

    # -- Prediction type 2: AGP Off-Track Risk --

    def predict_agp_off_track(self, advisor_id: str, persist: bool = True) -> dict:
        """Real-model tier first; AGP currently falls back (model below its quality gate),
        so this serves the deterministic scorecard until an AGP model passes the floor."""
        snapshot = self._snapshot(advisor_id)
        try:
            ms = get_model_client().score_risk(
                "AGP_OFF_TRACK_RISK", "ADVISOR", advisor_id, snapshot["features"])
            result = self._result_from_model(
                advisor_id, "AGP_OFF_TRACK_RISK", "PRED_AGPRISK", snapshot, ms, 90)
            if persist:
                self._persist(result)
            return result
        except ModelUnavailableError:
            pass
        f = snapshot["features"]
        track = AgpService(self.graph, today=self.as_of).track_status(advisor_id)
        if not track.get("enrolled"):
            return {"prediction_type": "AGP_OFF_TRACK_RISK", "target_id": advisor_id, "enrolled": False}

        components = track["components"]
        contributions = [
            {"feature": "milestone_attainment_pct", "value": f.get("milestone_attainment_pct"),
             "points": round(components["attainment_gap"] * components["weights"]["attainment_gap"], 1),
             "why": "gap between milestone attainment and target"},
            {"feature": "milestone_days_remaining", "value": f.get("milestone_days_remaining"),
             "points": round(components["time_pressure"] * components["weights"]["time_pressure"], 1),
             "why": "time remaining to the milestone due date"},
            {"feature": "overdue_followup_count", "value": f.get("overdue_followup_count"),
             "points": round(components["crm_execution_risk"] * components["weights"]["crm_execution_risk"], 1),
             "why": "pending/overdue CRM execution required by the milestone"},
        ]
        kpi_ratio = f.get("kpi_on_track_ratio")
        score = track["score"]
        if kpi_ratio is not None and float(kpi_ratio) < 0.5:
            bump = round((0.5 - float(kpi_ratio)) * 30, 1)
            score = round(min(100.0, score + bump), 1)
            contributions.append({"feature": "kpi_on_track_ratio", "value": kpi_ratio, "points": bump,
                                  "why": "fewer than half of KPI measurements on track"})

        used = [c["feature"] for c in contributions]
        agp_methodology = self._methodology("AGP_OFF_TRACK_RISK", contributions, score)
        agp_methodology["served_by"] = "scorecard"
        result = {
            "prediction_id": f"PRED_AGPRISK_{advisor_id}_{MODEL_VERSION}",
            "prediction_type": "AGP_OFF_TRACK_RISK",
            "target_type": "ADVISOR",
            "target_id": advisor_id,
            "score": score,
            "risk_band": _risk_band(score),
            "severity": _risk_band(score),
            "confidence": self._confidence(f, used),
            "horizon_days": 45,
            "contributions": contributions,
            "feature_snapshot_id": snapshot["snapshot_id"],
            "explanation": track["explanation"],
            "methodology": agp_methodology,
        }
        if persist:
            self._persist(result)
        return result

    def predict_advisor(self, advisor_id: str, persist: bool = True) -> dict:
        return {
            "advisor_id": advisor_id,
            "predictions": [
                self.predict_revenue_decline(advisor_id, persist),
                self.predict_agp_off_track(advisor_id, persist),
            ],
        }

    # -- persistence: prediction vertex + lineage edges + reasoning trace --

    def _persist(self, result: dict) -> None:
        record = {
            "prediction_id": result["prediction_id"],
            "prediction_type": result["prediction_type"],
            "target_type": result["target_type"],
            "target_id": result["target_id"],
            "score": result["score"],
            "confidence": result["confidence"],
            "risk_band": result["risk_band"],
            "severity": result["severity"],
            "horizon_days": result["horizon_days"],
            "explanation": result["explanation"],
            "status": "ACTIVE",
            "generated_at": self.as_of.isoformat(),
        }
        upsert_vertex(self.graph, "phx_dm_prediction_result", "prediction_id", record)
        upsert_edge(self.graph, "phx_dm_prediction_for_advisor", "phx_dm_prediction_result", "phx_dm_advisor",
                    result["prediction_id"], result["target_id"])
        upsert_edge(self.graph, "phx_dm_prediction_uses_feature_snapshot", "phx_dm_prediction_result",
                    "phx_dm_feature_snapshot", result["prediction_id"], result["feature_snapshot_id"])
        write_reasoning_trace(
            self.graph,
            reasoning_id=f"REASON_{result['prediction_id']}",
            artifact_type="PREDICTION",
            artifact_id=result["prediction_id"],
            steps=[
                "Load latest feature snapshot for the advisor",
                "Score each contributing feature with the documented weight",
                "Sum contributions and clamp to 0-100",
                "Band score to severity per the Severity_Model",
            ],
            evidence={"contributions": result["contributions"], "feature_snapshot_id": result["feature_snapshot_id"]},
            feature_snapshot_id=result["feature_snapshot_id"],
            created_at=self.as_of.isoformat(),
        )
