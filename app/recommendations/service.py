from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

from app.config.settings import get_settings
from app.graph.artifacts import upsert_edge, upsert_vertex, write_reasoning_trace
from app.graph.client import GraphClient, get_graph_client
from app.opportunities.service import OpportunityDetectionService

MODEL_VERSION = "v2.0"

# Opportunity category -> action family + playbook category. The learning loop
# stores a weight per action family; feedback moves it and future ranking shifts.
ACTION_FAMILIES = {
    "PRODUCT_MIX": {
        "family": "MANAGED_MIX",
        "playbook_category": "GROWTH",
        "title": "Run managed-account review sprints for top households",
        "action_text": (
            "Identify the highest-AUM households with low managed penetration, schedule advisory review "
            "meetings, and document suitability for a managed mandate."
        ),
    },
    "REVENUE_AT_RISK": {
        "family": "RETENTION",
        "playbook_category": "RETENTION",
        "title": "Launch a revenue retention sequence",
        "action_text": (
            "Contact households behind the negative cash-flow trend, confirm liquidity drivers, and schedule "
            "retention/planning conversations before quarter end."
        ),
    },
    "AGP_EXECUTION": {
        "family": "CRM_EXECUTION",
        "playbook_category": "AGP",
        "title": "Close the AGP milestone execution gap",
        "action_text": (
            "Complete overdue lead and referral follow-ups, advance the highest-value CRM opportunity, and "
            "book a coaching session before the milestone due date."
        ),
    },
    "PIPELINE_ACCELERATION": {
        "family": "CRM_EXECUTION",
        "playbook_category": "AGP",
        "title": "Accelerate the stalled CRM pipeline",
        "action_text": (
            "Work overdue follow-ups oldest-first, refresh next actions on every open opportunity, and "
            "advance or close stage-stalled deals."
        ),
    },
}


class LearningWeightStore:
    """Per-action-family ranking weights updated by feedback (the RL-style signal).
    Weight 1.0 is neutral; accepted/completed actions push it up, rejections down."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or get_settings().sqlite_db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS learning_weights (
                    family TEXT PRIMARY KEY, weight REAL NOT NULL, feedback_count INTEGER NOT NULL,
                    updated_at TEXT)"""
            )

    def weight(self, family: str) -> float:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT weight FROM learning_weights WHERE family = ?", (family,)).fetchone()
        return float(row[0]) if row else 1.0

    def apply_delta(self, family: str, delta: float, updated_at: str) -> float:
        current = self.weight(family)
        new_weight = round(max(0.5, min(1.5, current + delta)), 4)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO learning_weights (family, weight, feedback_count, updated_at) VALUES (?,?,1,?) "
                "ON CONFLICT(family) DO UPDATE SET weight=?, feedback_count=feedback_count+1, updated_at=?",
                (family, new_weight, updated_at, new_weight, updated_at),
            )
        return new_weight

    def all_weights(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT family, weight, feedback_count, updated_at FROM learning_weights ORDER BY family"
            ).fetchall()
        return [
            {"family": family, "weight": weight, "feedback_count": count, "updated_at": updated}
            for family, weight, count, updated in rows
        ]


class RecommendationService:
    """Ranked next-best-action generation: consumes AI opportunities, selects a
    playbook, applies the learning weight for the action family, and persists
    the full lineage chain (opportunity -> prediction -> features -> playbook
    -> reasoning). Rebuilt after the 0B audit found the prior engine clobbered."""

    def __init__(self, graph: GraphClient | None = None, as_of: date | None = None) -> None:
        self.graph = graph or get_graph_client()
        self.as_of = as_of or date(2026, 7, 3)
        self.opportunities = OpportunityDetectionService(self.graph, as_of=self.as_of)
        self.learning = LearningWeightStore()

    def _playbook_for(self, category: str) -> dict | None:
        merged: dict = {}
        for entry in self.graph.run_query("get_data_health_summary", {}).get("results", []):
            merged.update(entry)
        # playbooks are few; fetch directly from the store via a subgraph-free scan
        # (GraphClient has no playbook query in the catalog, so we filter client-side)
        from app.graph.client import MockGraphClient

        if isinstance(self.graph, MockGraphClient):
            for playbook_id, attrs in self.graph.store.all_vertices("phx_dm_playbook").items():
                if str(attrs.get("category", "")).upper() == category.upper():
                    return {"playbook_id": playbook_id, **attrs}
            first = next(iter(self.graph.store.all_vertices("phx_dm_playbook").items()), None)
            return {"playbook_id": first[0], **first[1]} if first else None
        return None  # live mode: playbook selection via installed query once added to the catalog

    def generate_for_advisor(self, advisor_id: str, persist: bool = True) -> dict:
        detection = self.opportunities.detect_for_advisor(advisor_id, persist=persist)
        recommendations = []
        for opp in detection["opportunities"]:
            mapping = ACTION_FAMILIES.get(opp["category"])
            if mapping is None:
                continue
            playbook = self._playbook_for(mapping["playbook_category"])
            weight = self.learning.weight(mapping["family"])
            base_priority = opp["score"]
            priority = round(min(100.0, base_priority * weight), 1)
            confidence = round(min(0.99, (opp["components"]["confidence_evidence"] / 100) * weight), 2)
            recommendation = {
                "recommendation_id": f"REC_{opp['opportunity_id']}",
                "recommendation_type": "NEXT_BEST_ACTION",
                "title": mapping["title"],
                "action_text": mapping["action_text"],
                "action_family": mapping["family"],
                "base_priority_score": base_priority,
                "learning_weight": weight,
                "priority_score": priority,
                "severity": opp["severity"],
                "confidence": confidence,
                "estimated_revenue_impact": opp["estimated_revenue_impact"],
                "opportunity_id": opp["opportunity_id"],
                "prediction_id": opp.get("derived_from_prediction"),
                "playbook_id": playbook["playbook_id"] if playbook else None,
                "status": "PRESENTED",
            }
            recommendations.append(recommendation)

        recommendations.sort(key=lambda r: -r["priority_score"])
        if persist:
            for rec in recommendations:
                self._persist(rec, advisor_id, detection["feature_snapshot_id"])
        return {
            "advisor_id": advisor_id,
            "recommendations": recommendations,
            "learning_weights": self.learning.all_weights(),
            "feature_snapshot_id": detection["feature_snapshot_id"],
        }

    def _persist(self, rec: dict, advisor_id: str, snapshot_id: str) -> None:
        record = {
            "recommendation_id": rec["recommendation_id"],
            "recommendation_type": rec["recommendation_type"],
            "title": rec["title"],
            "action_text": rec["action_text"],
            "priority_score": rec["priority_score"],
            "severity": rec["severity"].upper(),
            "confidence": rec["confidence"],
            "estimated_revenue_impact": rec["estimated_revenue_impact"],
            "status": rec["status"],
            "generated_at": self.as_of.isoformat(),
        }
        upsert_vertex(self.graph, "phx_dm_recommendation", "recommendation_id", record)
        upsert_edge(self.graph, "phx_dm_recommendation_for_advisor", "phx_dm_recommendation", "phx_dm_advisor",
                    rec["recommendation_id"], advisor_id)
        upsert_edge(self.graph, "phx_dm_recommendation_addresses_opportunity", "phx_dm_recommendation",
                    "phx_dm_opportunity", rec["recommendation_id"], rec["opportunity_id"])
        upsert_edge(self.graph, "phx_dm_recommendation_uses_feature_snapshot", "phx_dm_recommendation",
                    "phx_dm_feature_snapshot", rec["recommendation_id"], snapshot_id)
        if rec.get("prediction_id"):
            upsert_edge(self.graph, "phx_dm_recommendation_based_on_prediction", "phx_dm_recommendation",
                        "phx_dm_prediction_result", rec["recommendation_id"], rec["prediction_id"])
        if rec.get("playbook_id"):
            upsert_edge(self.graph, "phx_dm_recommendation_uses_playbook", "phx_dm_recommendation",
                        "phx_dm_playbook", rec["recommendation_id"], rec["playbook_id"])
        write_reasoning_trace(
            self.graph,
            reasoning_id=f"REASON_{rec['recommendation_id']}",
            artifact_type="RECOMMENDATION",
            artifact_id=rec["recommendation_id"],
            steps=[
                "Take the highest-severity open AI opportunities for the advisor",
                "Map the opportunity category to an action family and playbook",
                f"Apply the learned ranking weight for {rec['action_family']} ({rec['learning_weight']})",
                "Rank by adjusted priority and persist the full lineage chain",
            ],
            evidence={
                "opportunity_id": rec["opportunity_id"],
                "prediction_id": rec.get("prediction_id"),
                "playbook_id": rec.get("playbook_id"),
                "base_priority_score": rec["base_priority_score"],
                "learning_weight": rec["learning_weight"],
                "adjusted_priority_score": rec["priority_score"],
            },
            feature_snapshot_id=snapshot_id,
            created_at=self.as_of.isoformat(),
        )
