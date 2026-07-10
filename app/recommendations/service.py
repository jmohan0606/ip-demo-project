from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path

from app.config.settings import get_settings
from app.graph.artifacts import upsert_edge, upsert_vertex, write_reasoning_trace
from app.graph.client import GraphClient, get_graph_client
from app.graph.queries.common import graph_fallback_store, run_catalog_query
from app.opportunities.service import OpportunityDetectionService
from app.shared.ids import new_id

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
    Weight 1.0 is neutral; accepted/completed actions push it up, rejections down.

    Now a thin facade over the StateRepository adapter — the weights live in TigerGraph
    (phx_dm_learning_weight vertices) as the source of truth, with SQLite fallback. No
    direct sqlite3 here anymore (see DATABASES.md / StateRepository)."""

    def __init__(self, db_path: str | None = None) -> None:
        from app.repositories.state_repository import get_state_repository

        self._state = get_state_repository()

    def weight(self, family: str) -> float:
        return self._state.get_learning_weight(family)

    def apply_delta(self, family: str, delta: float, updated_at: str) -> float:
        return self._state.apply_learning_delta(family, delta, updated_at)

    def all_weights(self) -> list[dict]:
        return self._state.all_learning_weights()


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
        from app.recommendations.lifecycle import RecommendationLifecycleService
        self.lifecycle = RecommendationLifecycleService()
        from app.recommendations.compliance_validator import RecommendationComplianceValidator
        self._compliance = RecommendationComplianceValidator()

    def _playbook_for(self, category: str) -> dict | None:
        merged: dict = {}
        for entry in self.graph.run_query("get_data_health_summary", {}).get("results", []):
            merged.update(entry)
        # Playbook listing via GQ-059 get_playbooks (run_query — real TigerGraph in
        # real mode, previously impossible: live mode returned None here). Category
        # matching stays client-side. The direct store scan below survives only as
        # the logged fallback.
        results = run_catalog_query(self.graph, "get_playbooks", {})
        if results is not None:
            for entry in results:
                if entry.get("playbooks") is None:
                    continue
                rows = [(str(r.get("v_id")), r.get("attributes", {})) for r in entry["playbooks"]]
                for playbook_id, attrs in rows:
                    if str(attrs.get("category", "")).upper() == category.upper():
                        return {"playbook_id": playbook_id, **attrs}
                return {"playbook_id": rows[0][0], **rows[0][1]} if rows else None
        # fallback: original store scan (run_catalog_query already logged it)
        store = graph_fallback_store(self.graph)
        for playbook_id, attrs in store.all_vertices("phx_dm_playbook").items():
            if str(attrs.get("category", "")).upper() == category.upper():
                return {"playbook_id": playbook_id, **attrs}
        first = next(iter(store.all_vertices("phx_dm_playbook").items()), None)
        return {"playbook_id": first[0], **first[1]} if first else None

    @staticmethod
    def _outcome_affinities(advisor_id: str) -> dict[str, float]:
        """Per-family outcome-driven-learning affinity for the advisor (Section 11.3).
        Empty until the GNN has been fine-tuned on recorded outcomes; never blocks generation."""
        try:
            from app.ml.fl_service import family_affinity
            return family_affinity(advisor_id)
        except Exception:
            return {}

    @staticmethod
    def _affinity_block(family: str, affinities: dict[str, float]) -> dict | None:
        if family not in affinities:
            return None
        val = affinities[family]
        tone = "a positive" if val > 0.02 else ("a negative" if val < -0.02 else "a neutral")
        return {
            "value": round(float(val), 4),
            "sentence": f"Advisors in situations like this one have {tone} recorded track record "
                        f"with {family.replace('_', ' ').title()} actions (affinity {val:+.2f}, "
                        f"outcome-driven learning).",
        }

    def generate_for_advisor(self, advisor_id: str, persist: bool = True) -> dict:
        # Section 13B.1: time the real pipeline stages so the SYSTEM TRACE bar shows genuine
        # per-stage execution timing (this is the first real producer of observability stage spans).
        from app.observability import recorder as _rec
        _spans: list[dict] = []
        with _rec.stage_timer("Feature + Prediction + Opportunity detection", _spans):
            detection = self.opportunities.detect_for_advisor(advisor_id, persist=persist)
        _map_timer = _rec.stage_timer("Recommendation mapping (opportunity → next-best-action)", _spans)
        _map_timer.__enter__()
        affinities = self._outcome_affinities(advisor_id)
        # Section 13.5: opportunities already addressed by a COMPLETED recommendation are
        # not re-issued — they surface as an "Addressed" list instead.
        addressed = self.lifecycle.addressed_opportunity_ids(advisor_id)
        addressed_out = []
        recommendations = []
        for opp in detection["opportunities"]:
            if opp["opportunity_id"] in addressed:
                entry = self.lifecycle.ledger_for_opportunity(opp["opportunity_id"])
                addressed_out.append({
                    "opportunity_id": opp["opportunity_id"], "category": opp["category"],
                    "severity": opp.get("severity"),
                    "addressed_by": (entry or {}).get("recommendation_id"),
                    "completed_ts": (entry or {}).get("created_ts"),
                    "note": (entry or {}).get("note"),
                })
                continue
            mapping = ACTION_FAMILIES.get(opp["category"])
            if mapping is None:
                continue
            playbook = self._playbook_for(mapping["playbook_category"])
            weight = self.learning.weight(mapping["family"])
            base_priority = opp["score"]
            priority = round(min(100.0, base_priority * weight), 1)
            confidence = round(min(0.99, (opp["components"]["confidence_evidence"] / 100) * weight), 2)
            # Section 11.3: outcome-driven-learning affinity — evidence always; a bounded
            # ±10% confidence modifier when enabled. Does NOT touch priority (bandit owns rank).
            outcome_affinity = self._affinity_block(mapping["family"], affinities)
            if outcome_affinity and get_settings().fl_affinity_in_confidence:
                import math
                mod = max(0.90, min(1.10, 1 + 0.15 * math.tanh(2 * outcome_affinity["value"])))
                confidence = round(min(0.99, confidence * mod), 2)
                outcome_affinity["confidence_modifier"] = round(mod, 3)
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
                "outcome_affinity": outcome_affinity,
                "status": "PRESENTED",
            }
            # Section 13B.1: run the real compliance validator on the live path so the
            # rec carries a real verdict (Context & Compliance stage of the pipeline trace).
            c_status, c_warnings = self._compliance.validate(
                mapping["action_text"], opp.get("rationale", ""),
                [opp["opportunity_id"], recommendation["playbook_id"] or "", recommendation["prediction_id"] or ""],
            )
            recommendation["compliance"] = {"status": c_status.value.upper(), "warnings": c_warnings}
            recommendations.append(recommendation)

        recommendations.sort(key=lambda r: -r["priority_score"])
        _map_timer.__exit__()
        if persist:
          with _rec.stage_timer("Persist + lifecycle register + explainability trace", _spans):
            for rec in recommendations:
                self._persist(rec, advisor_id, detection["feature_snapshot_id"])
                # Section 13.1: register in the durable lifecycle mirror (status-preserving)
                # and merge the authoritative status / allowed_actions onto the response.
                lc = self.lifecycle.register_generated(rec, advisor_id)
                rec["status"] = lc["status"]
                rec["status_note"] = lc["status_note"]
                rec["allowed_actions"] = lc["allowed_actions"]
                rec["terminal"] = lc["terminal"]
        _rec.record_stage(f"recommendation-pipeline {advisor_id}", _spans)
        return {
            "advisor_id": advisor_id,
            "recommendations": recommendations,
            "learning_weights": self.learning.all_weights(),
            "feature_snapshot_id": detection["feature_snapshot_id"],
            "lifecycle_counts": self.lifecycle.counts_for_advisor(advisor_id) if persist else {},
            "addressed_opportunities": addressed_out,
        }

    def list_for_advisor(self, advisor_id: str) -> dict:
        """Read the persisted recommendation vertices for an advisor via the installed
        GQ-028 get_recommendations query (recommendation_for_advisor traversal) —
        includes engine-generated recs AND ones saved from the What-If Simulator,
        since both go through the same real pipeline. The direct store read below
        survives ONLY as the logged fallback path."""
        from app.graph.queries.common import graph_fallback_store, run_catalog_query

        def _row(rid: str, r: dict) -> dict:
            return {
                "recommendation_id": r.get("recommendation_id", rid),
                "recommendation_type": r.get("recommendation_type"),
                "title": r.get("title"),
                "action_text": r.get("action_text"),
                "severity": r.get("severity"),
                "priority_score": r.get("priority_score"),
                "confidence": r.get("confidence"),
                "estimated_revenue_impact": r.get("estimated_revenue_impact"),
                "impact_summary": r.get("impact_summary"),
                "status": r.get("status"),
                "generated_at": r.get("generated_at"),
            }

        recs: list[dict] = []
        results = run_catalog_query(
            self.graph, "get_recommendations", {"target_type": "ADVISOR", "target_id": advisor_id}
        )
        if results is not None:
            for entry in results:
                for row in entry.get("recommendations") or []:
                    recs.append(_row(str(row.get("v_id")), row.get("attributes", {}) or {}))
        else:
            store = graph_fallback_store(self.graph)
            for rid in store.in_ids("phx_dm_recommendation_for_advisor", advisor_id):
                recs.append(_row(rid, store.vertex("phx_dm_recommendation", rid) or {}))
        recs.sort(key=lambda r: float(r.get("priority_score") or 0), reverse=True)
        return {"advisor_id": advisor_id, "recommendations": recs}

    def _latest_snapshot_id(self, advisor_id: str) -> str | None:
        """Latest feature-snapshot id for the advisor via the installed GQ-022
        get_feature_snapshot query (snapshot_time DESC in GSQL; sorted defensively
        here for the mock). The direct advisor_has_feature_snapshot edge read
        survives ONLY as the logged fallback path."""
        from app.graph.queries.common import run_catalog_query

        results = run_catalog_query(
            self.graph, "get_feature_snapshot", {"entity_type": "ADVISOR", "entity_id": advisor_id}
        )
        if results is not None:
            for entry in results:
                snaps = entry.get("feature_snapshots") or []
                if snaps:
                    snaps = sorted(
                        snaps,
                        key=lambda s: str((s.get("attributes") or {}).get("snapshot_time", "")),
                        reverse=True,
                    )
                    return str(snaps[0].get("v_id"))
            return None
        # fallback: the original direct-store edge read (only when the query failed)
        store = getattr(self.graph, "store", None)
        if store is not None:
            ids = store.out_ids("phx_dm_advisor_has_feature_snapshot", advisor_id)
            return str(ids[0]) if ids else None
        return None

    def save_scenario_as_recommendation(
        self,
        advisor_id: str,
        title: str,
        category: str,
        levers: dict,
        metrics: list[dict],
        snapshot_id: str | None = None,
        high_priority: bool = False,
        created_date: str | None = None,
    ) -> dict:
        """Persist a What-If scenario result as a REAL recommendation through the same
        pipeline generate_for_advisor uses (recommendation vertex + for_advisor /
        uses_feature_snapshot edges + reasoning trace) — NOT a separate table
        (CLAUDE.md 9.5). Also stores the scenario itself for provenance."""
        when = created_date or self.as_of.isoformat()
        snapshot_id = snapshot_id or self._latest_snapshot_id(advisor_id)

        # 1) persist the saved scenario for provenance
        scenario_id = new_id("SCENW")
        revenue_metric = next((m for m in metrics if str(m.get("metric")).lower().startswith("total revenue")), None)
        revenue_impact = round(float(revenue_metric["change"]), 2) if revenue_metric else 0.0
        upsert_vertex(self.graph, "phx_dm_simulation_scenario", "scenario_id", {
            "scenario_id": scenario_id,
            "scenario_type": "WHATIF_SAVED",
            "scope_type": "ADVISOR",
            "scope_id": advisor_id,
            "assumptions_json": json.dumps(levers),
            "baseline_json": json.dumps({m["metric"]: m.get("current") for m in metrics}),
            "projected_json": json.dumps({m["metric"]: m.get("projected") for m in metrics}),
            "created_at": when,
        })
        upsert_edge(self.graph, "phx_dm_scenario_for_advisor", "phx_dm_simulation_scenario",
                    "phx_dm_advisor", scenario_id, advisor_id)

        # 2) persist the recommendation through the real chain
        rec_id = new_id("REC_WHATIF")
        lever_txt = ", ".join(f"{k.replace('_', ' ')}={v}" for k, v in levers.items() if v)
        action_text = (
            f"Execute the modelled scenario ({lever_txt or 'baseline levers'}). Projected impact: "
            + "; ".join(f"{m['metric']} {m['change']:+.0f}{'%' if m['unit']=='pts' else ''}" for m in metrics[:3])
            + f". Save-as-recommendation from the What-If Simulator for {advisor_id}."
        )
        record = {
            "recommendation_id": rec_id,
            "recommendation_type": "SCENARIO_ACTION",
            "title": title,
            "action_text": action_text,
            "priority_score": 92.0 if high_priority else 62.0,
            "severity": "CRITICAL" if high_priority else "ATTENTION",
            "confidence": 0.72,
            "estimated_revenue_impact": revenue_impact,
            "impact_summary": f"What-If scenario · category {category}",
            "status": "PRESENTED",
            "generated_at": when,
        }
        upsert_vertex(self.graph, "phx_dm_recommendation", "recommendation_id", record)
        upsert_edge(self.graph, "phx_dm_recommendation_for_advisor", "phx_dm_recommendation",
                    "phx_dm_advisor", rec_id, advisor_id)
        if snapshot_id:
            upsert_edge(self.graph, "phx_dm_recommendation_uses_feature_snapshot", "phx_dm_recommendation",
                        "phx_dm_feature_snapshot", rec_id, snapshot_id)
        write_reasoning_trace(
            self.graph,
            reasoning_id=f"REASON_{rec_id}",
            artifact_type="RECOMMENDATION",
            artifact_id=rec_id,
            steps=[
                "Manager ran a What-If scenario over the advisor's real current feature snapshot",
                f"Applied levers: {lever_txt or 'none'}",
                "Projected impact via the documented What-If elasticities (transparent formula)",
                f"Saved as a {('high-priority ' if high_priority else '')}recommendation in category {category}",
            ],
            evidence={
                "scenario_id": scenario_id,
                "category": category,
                "high_priority": high_priority,
                "levers": levers,
                "projected_metrics": {m["metric"]: m.get("projected") for m in metrics},
            },
            feature_snapshot_id=snapshot_id,
            created_at=when,
        )
        return {
            "saved": True,
            "recommendation_id": rec_id,
            "scenario_id": scenario_id,
            "advisor_id": advisor_id,
            "category": category,
            "high_priority": high_priority,
            "estimated_revenue_impact": revenue_impact,
            **record,
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
