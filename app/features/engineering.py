from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from app.agp.service import AgpService
from app.crm.service import CrmService
from app.graph.client import GraphClient, get_graph_client

FEATURE_VERSION = "v2.0"


@dataclass
class FeatureValue:
    name: str
    value: Any
    group: str
    source: str  # which query/service produced it
    evidence: dict = field(default_factory=dict)  # ids/figures the value derives from


@dataclass
class FeatureSnapshot:
    snapshot_id: str
    entity_type: str
    entity_id: str
    snapshot_time: str
    feature_version: str
    features: list[FeatureValue]

    def values(self) -> dict[str, Any]:
        return {f.name: f.value for f in self.features}

    def lineage(self) -> dict[str, dict]:
        return {f.name: {"group": f.group, "source": f.source, "evidence": f.evidence} for f in self.features}


def _merged(graph: GraphClient, query: str, params: dict) -> dict:
    merged: dict = {}
    for entry in graph.run_query(query, params).get("results", []):
        merged.update(entry)
    return merged


class FeatureEngineeringService:
    """Feature engine per spec Section 9: queries the graph via GraphClient,
    computes the Feature_Catalog features with per-feature lineage, and
    persists a versioned snapshot (SQLite + phx_dm_feature_snapshot vertex)."""

    def __init__(self, graph: GraphClient | None = None, as_of: date | None = None) -> None:
        self.graph = graph or get_graph_client()
        self.as_of = as_of or date(2026, 7, 3)  # deterministic anchor aligned with seed data
        self.crm = CrmService(self.graph, today=self.as_of)
        self.agp = AgpService(self.graph, today=self.as_of)

    # -- window helpers --

    def _window(self, months: int, end: date | None = None) -> tuple[str, str]:
        end = end or (self.as_of.replace(day=1) - timedelta(days=1))  # last complete month end
        start = (end.replace(day=1) - timedelta(days=months * 31 - 15)).replace(day=1)
        return start.isoformat(), end.isoformat()

    def _revenue_summary(self, advisor_id: str, months: int, end: date | None = None) -> dict:
        start_date, end_date = self._window(months, end)
        return _merged(
            self.graph,
            "get_revenue_summary_by_scope",
            {"scope_type": "ADVISOR", "scope_id": advisor_id, "period_type": "CUSTOM",
             "start_date": start_date, "end_date": end_date},
        )

    # -- main entry point --

    def compute_advisor_snapshot(self, advisor_id: str) -> FeatureSnapshot:
        features: list[FeatureValue] = []
        add = features.append

        # ---- Revenue group ----
        ltm = self._revenue_summary(advisor_id, 12)
        prior_3m_end = (self.as_of.replace(day=1) - timedelta(days=1)).replace(day=1) - timedelta(days=1)
        prior_3m_end = (prior_3m_end.replace(day=1) - timedelta(days=62)).replace(day=1) - timedelta(days=1)
        last_3m = self._revenue_summary(advisor_id, 3)
        prev_3m = self._revenue_summary(advisor_id, 3, end=prior_3m_end)
        revenue_ltm = float(ltm.get("total_revenue") or 0)
        add(FeatureValue("revenue_ltm", round(revenue_ltm, 2), "Revenue", "GQ-004 get_revenue_summary_by_scope",
                         {"window": self._window(12), "transaction_count": ltm.get("transaction_count")}))
        r3, r3p = float(last_3m.get("total_revenue") or 0), float(prev_3m.get("total_revenue") or 0)
        growth_3m = round((r3 - r3p) / r3p * 100, 2) if r3p else 0.0
        add(FeatureValue("revenue_growth_3m_pct", growth_3m, "Revenue", "GQ-004 two 3-month windows",
                         {"last_3m": r3, "prev_3m": r3p}))

        mix = _merged(self.graph, "get_product_mix_by_scope",
                      {"scope_type": "ADVISOR", "scope_id": advisor_id,
                       "start_date": self._window(12)[0], "end_date": self._window(12)[1]})
        managed_ids = {
            p["v_id"] for p in mix.get("products", []) if p.get("attributes", {}).get("managed_flag")
        }
        total_mix_rev = sum(float(r.get("revenue") or 0) for r in mix.get("product_mix", []))
        managed_rev = sum(
            float(r.get("revenue") or 0) for r in mix.get("product_mix", []) if r.get("product_id") in managed_ids
        )
        managed_ratio = round(managed_rev / total_mix_rev, 4) if total_mix_rev else 0.0
        add(FeatureValue("managed_revenue_ratio", managed_ratio, "Revenue", "GQ-006 get_product_mix_by_scope",
                         {"managed_revenue": round(managed_rev, 2), "total_revenue": round(total_mix_rev, 2),
                          "managed_product_ids": sorted(managed_ids)}))
        # product diversification: 1 - Herfindahl index over product revenue shares
        shares = [float(r.get("revenue") or 0) / total_mix_rev for r in mix.get("product_mix", [])] if total_mix_rev else []
        diversification = round(1 - sum(s * s for s in shares), 4) if shares else 0.0
        add(FeatureValue("product_diversification_score", diversification, "Revenue", "GQ-006 (1 - HHI of shares)",
                         {"product_count": len(shares)}))

        # ---- Book group ----
        add(FeatureValue("household_count", int(ltm.get("household_count") or 0), "Book", "GQ-004", {}))
        add(FeatureValue("account_count", int(ltm.get("account_count") or 0), "Book", "GQ-004", {}))
        aum_now = float(last_3m.get("ending_aum") or 0)
        aum_prev = float(prev_3m.get("ending_aum") or 0)
        add(FeatureValue("aum_total", round(aum_now, 2), "Book", "GQ-004 ending_aum", {"month_end": self._window(3)[1]}))
        aum_growth = round((aum_now - aum_prev) / aum_prev * 100, 2) if aum_prev else 0.0
        add(FeatureValue("aum_growth_3m_pct", aum_growth, "Book", "GQ-004 two windows",
                         {"aum_now": aum_now, "aum_prev": aum_prev}))
        add(FeatureValue("ncf_3m", round(float(last_3m.get("total_ncf") or 0), 2), "Book", "GQ-004", {}))
        add(FeatureValue("nnm_3m", round(float(last_3m.get("total_nnm") or 0), 2), "Book", "GQ-004", {}))

        # ---- Peer group ----
        peer = _merged(self.graph, "get_peer_benchmark",
                       {"advisor_id": advisor_id, "peer_method": "MARKET",
                        "start_date": self._window(12)[0], "end_date": self._window(12)[1]})
        peer_count = int(peer.get("peer_count") or 0)
        peer_avg = float(peer.get("peer_revenue_sum") or 0) / peer_count if peer_count else 0.0
        peer_gap = round((revenue_ltm - peer_avg) / peer_avg * 100, 2) if peer_avg else 0.0
        add(FeatureValue("peer_revenue_gap_pct", peer_gap, "Peer", "GQ-008 get_peer_benchmark",
                         {"peer_avg_revenue": round(peer_avg, 2), "peer_count": peer_count}))

        # ---- CRM group (via CrmService, CRM-005) ----
        crm_inputs = self.crm.feature_inputs(advisor_id)
        leads = self.crm.leads(advisor_id)["summary"]
        referrals = self.crm.referrals(advisor_id)["summary"]
        crm_lineage = crm_inputs["lineage"]
        add(FeatureValue("pending_lead_count", leads["pending"], "CRM", "CrmService.leads", crm_lineage))
        add(FeatureValue("completed_lead_count", leads["completed"], "CRM", "CrmService.leads", {}))
        add(FeatureValue("lead_completion_rate", leads["completion_rate_pct"], "CRM", "CrmService.leads", {}))
        add(FeatureValue("lead_conversion_rate", leads["conversion_rate_pct"], "CRM", "CrmService.leads", {}))
        add(FeatureValue("pending_referral_count", referrals["pending"], "CRM", "CrmService.referrals", {}))
        add(FeatureValue("referral_completion_rate", referrals["completion_rate_pct"], "CRM", "CrmService.referrals", {}))
        add(FeatureValue("referral_conversion_rate", referrals["conversion_rate_pct"], "CRM", "CrmService.referrals", {}))
        add(FeatureValue("crm_pipeline_value", crm_inputs["features"]["crm_open_pipeline_amount"], "CRM",
                         "CrmService.pipeline_by_stage", {"stages": crm_lineage["pipeline_stages"]}))
        add(FeatureValue("weighted_pipeline_value", crm_inputs["features"]["crm_open_pipeline_weighted"], "CRM",
                         "CrmService.pipeline_by_stage", {}))
        add(FeatureValue("overdue_followup_count", leads["overdue"] + referrals["overdue"], "CRM",
                         "CrmService leads+referrals overdue", {}))

        a360 = _merged(self.graph, "get_advisor_360", {"advisor_id": advisor_id})
        activity_dates = sorted(
            (str(a.get("attributes", {}).get("activity_date") or "") for a in a360.get("crm_activities", [])),
            reverse=True,
        )
        days_since = None
        if activity_dates and activity_dates[0]:
            latest = date.fromisoformat(activity_dates[0][:10])
            days_since = (self.as_of - latest).days
        add(FeatureValue("days_since_last_client_activity", days_since, "CRM", "GQ-009 crm_activities",
                         {"latest_activity_date": activity_dates[0] if activity_dates else None}))

        # ---- AGP group (via AgpService) ----
        track = self.agp.track_status(advisor_id)
        if track.get("enrolled"):
            enrollment = self.agp.enrollment_summary(advisor_id)["enrollments"][0]
            add(FeatureValue("agp_program_month", enrollment["current_program_month"], "AGP",
                             "AgpService.enrollment_summary", {"enrollment_id": enrollment["enrollment_id"]}))
            current = track.get("current_milestone") or {}
            add(FeatureValue("milestone_attainment_pct", current.get("attainment_pct"), "AGP",
                             "AgpService.track_status", {"milestone_progress_id": current.get("milestone_progress_id")}))
            add(FeatureValue("milestone_days_remaining", current.get("days_remaining"), "AGP",
                             "AgpService.track_status", {}))
            add(FeatureValue("agp_risk_score", track["score"], "AGP", "AgpService.track_status (AGP-004)",
                             track["components"]))
            timeline = self.agp.milestone_timeline(enrollment["enrollment_id"])
            statuses = [str(m.get("status", "")).upper() for m in timeline["measurements"]]
            on_track_ratio = round(statuses.count("ON_TRACK") / len(statuses), 4) if statuses else None
            add(FeatureValue("kpi_on_track_ratio", on_track_ratio, "AGP", "GQ-014 measurements",
                             {"measurement_count": len(statuses)}))
        else:
            add(FeatureValue("agp_program_month", None, "AGP", "AgpService (not enrolled)", {}))

        # ---- Feedback group ----
        recs = a360.get("recommendations", [])
        accepted = completed = presented = 0
        feedback_rec_ids = []
        for rec in recs:
            presented += 1
            history = _merged(self.graph, "get_feedback_learning_history", {"recommendation_id": rec["v_id"]})
            for fb in history.get("feedback", []):
                action = str(fb.get("attributes", {}).get("action") or fb.get("attributes", {}).get("feedback_action", "")).upper()
                if action in {"ACCEPT", "ACCEPTED"}:
                    accepted += 1
                    feedback_rec_ids.append(rec["v_id"])
                if action in {"COMPLETE", "COMPLETED"}:
                    completed += 1
        add(FeatureValue("recommendation_acceptance_rate", round(accepted / presented * 100, 1) if presented else None,
                         "Feedback", "GQ-030 per recommendation", {"presented": presented, "accepted": accepted,
                                                                    "recommendation_ids": [r["v_id"] for r in recs]}))
        add(FeatureValue("recommendation_completion_rate", round(completed / accepted * 100, 1) if accepted else None,
                         "Feedback", "GQ-030 per recommendation", {"completed": completed}))

        # ---- Graph group ----
        degree = sum(len(a360.get(k, [])) for k in
                     ("households", "accounts", "crm_activities", "crm_leads", "crm_referrals",
                      "crm_opportunities", "enrollments", "recommendations", "memories"))
        centrality = round(min(1.0, degree / 100), 4)
        add(FeatureValue("advisor_degree_centrality", centrality, "Graph", "GQ-009 relationship counts",
                         {"degree": degree}))

        # ---- Risk group (derived, components preserved) ----
        churn_pressure = max(0.0, -float(last_3m.get("total_ncf") or 0))
        revenue_at_risk = round(revenue_ltm * min(0.35, churn_pressure / max(aum_now, 1) * 4 + max(0, -growth_3m) / 100), 2)
        add(FeatureValue("revenue_at_risk_estimate", revenue_at_risk, "Risk",
                         "derived: revenue_ltm x risk factor(ncf outflow, negative growth)",
                         {"churn_pressure_ncf": churn_pressure, "revenue_growth_3m_pct": growth_3m}))
        client_value = round(min(100.0, (aum_now / 20_000_000) * 50 + (revenue_ltm / 500_000) * 50), 1)
        add(FeatureValue("client_value_score", client_value, "Risk", "derived: normalized AUM + revenue",
                         {"aum_total": aum_now, "revenue_ltm": revenue_ltm}))
        days_remaining = (track.get("current_milestone") or {}).get("days_remaining") if track.get("enrolled") else None
        overdue_total = leads["overdue"] + referrals["overdue"]
        time_sensitivity = round(min(100.0, (0 if days_remaining is None else max(0, 90 - days_remaining)) + overdue_total * 10), 1)
        add(FeatureValue("time_sensitivity_score", time_sensitivity, "Risk",
                         "derived: milestone proximity + overdue follow-ups",
                         {"milestone_days_remaining": days_remaining, "overdue_items": overdue_total}))

        snapshot_id = f"FS_{advisor_id}_{self.as_of.strftime('%Y%m%d')}_{FEATURE_VERSION}"
        return FeatureSnapshot(
            snapshot_id=snapshot_id,
            entity_type="ADVISOR",
            entity_id=advisor_id,
            snapshot_time=self.as_of.isoformat(),
            feature_version=FEATURE_VERSION,
            features=features,
        )

    # -- persistence: SQLite + graph artifact (traceability non-negotiable) --

    def ensure_graph_artifact(self, snapshot_dict: dict) -> None:
        """Re-upsert the snapshot vertex+edge if absent from the active graph —
        needed when a snapshot is served from SQLite in a fresh mock session
        (live TigerGraph persists, the in-memory mock does not)."""
        self._upsert_graph_artifact(
            snapshot_id=snapshot_dict["snapshot_id"],
            entity_type=snapshot_dict["entity_type"],
            entity_id=snapshot_dict["entity_id"],
            feature_version=snapshot_dict["feature_version"],
            snapshot_time=snapshot_dict["snapshot_time"],
            values=snapshot_dict["features"],
        )

    def persist_snapshot(self, snapshot: FeatureSnapshot) -> dict:
        from app.features.snapshot_store import SnapshotStore

        store = SnapshotStore()
        store.save(snapshot)
        self._upsert_graph_artifact(
            snapshot_id=snapshot.snapshot_id,
            entity_type=snapshot.entity_type,
            entity_id=snapshot.entity_id,
            feature_version=snapshot.feature_version,
            snapshot_time=snapshot.snapshot_time,
            values=snapshot.values(),
        )
        return {"snapshot_id": snapshot.snapshot_id, "persisted": True, "feature_count": len(snapshot.features)}

    def _upsert_graph_artifact(self, snapshot_id: str, entity_type: str, entity_id: str,
                               feature_version: str, snapshot_time: str, values: dict) -> None:
        entry = {
            "kind": "vertex",
            "target": "phx_dm_feature_snapshot",
            "id_column": "feature_snapshot_id",
            "file": "runtime",
            "columns": {
                "feature_snapshot_id": "feature_snapshot_id",
                "entity_type": "entity_type",
                "entity_id": "entity_id",
                "feature_group": "feature_group",
                "feature_version": "feature_version",
                "snapshot_time": "snapshot_time",
                "features_json": "features_json",
            },
        }
        self.graph.upsert(entry, [{
            "feature_snapshot_id": snapshot_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "feature_group": "ADVISOR_FULL",
            "feature_version": feature_version,
            "snapshot_time": snapshot_time,
            "features_json": json.dumps(values),
        }])
        edge_entry = {
            "kind": "edge",
            "target": "phx_dm_advisor_has_feature_snapshot",
            "from_type": "phx_dm_advisor",
            "to_type": "phx_dm_feature_snapshot",
            "from_column": "from_id",
            "to_column": "to_id",
            "file": "runtime",
            "columns": {},
        }
        self.graph.upsert(edge_entry, [{"from_id": entity_id, "to_id": snapshot_id}])
