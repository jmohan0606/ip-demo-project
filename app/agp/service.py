from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from app.graph.client import GraphClient, get_graph_client
from app.graph.queries.common import graph_fallback_store, run_catalog_query

logger = logging.getLogger(__name__)

# Severity bands per spec Section 7 (Severity_Model)
SEVERITY_BANDS = [
    (0, 39, "info"),
    (40, 69, "attention"),
    (70, 84, "urgent"),
    (85, 100, "critical"),
]

# AGP-004 on/off-track status derived from the same score scale
TRACK_BANDS = [
    (0, 39, "on_track"),
    (40, 69, "attention"),
    (70, 84, "urgent"),
    (85, 100, "critical"),
]

MILESTONE_MONTHS = [3, 6, 9, 12, 15, 18, 21, 24]  # AGP-002


def _band(score: float, bands: list[tuple[int, int, str]]) -> str:
    # Treat each band's integer `high` as "up to (high+1) exclusive" so fractional scores in the
    # old inter-band gaps (e.g. 39.9) classify into the lower band instead of falling through.
    for low, high, label in bands:
        if score < high + 1:
            return label
    return bands[-1][2]


def _attrs(vertex: dict) -> dict:
    return vertex.get("attributes", {})


def _parse_date(value: Any) -> date | None:
    text = str(value or "")[:10]
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


class AgpService:
    """AGP domain logic (AGP-001..006): 24-month program state, milestone
    timeline, KPI attainment and the on/off-track risk calculation, computed
    from graph data via GraphClient — never hardcoded."""

    def __init__(self, graph: GraphClient | None = None, today: date | None = None) -> None:
        self.graph = graph or get_graph_client()
        self.today = today or date.today()

    # -- AGP-001: enrollment summary with current month / expected completion --

    def enrollment_summary(self, advisor_id: str) -> dict:
        result = self.graph.run_query("get_agp_enrollment_summary", {"advisor_id": advisor_id})
        merged: dict = {}
        for entry in result.get("results", []):
            merged.update(entry)
        enrollments = []
        for enrollment in merged.get("enrollments", []):
            attrs = _attrs(enrollment)
            start = _parse_date(attrs.get("start_date"))
            expected_end = _parse_date(attrs.get("expected_end_date"))
            months_elapsed = None
            if start:
                months_elapsed = (self.today.year - start.year) * 12 + (self.today.month - start.month)
            enrollments.append(
                {
                    "enrollment_id": enrollment.get("v_id"),
                    "cohort": attrs.get("cohort"),
                    "status": attrs.get("status"),
                    "start_date": attrs.get("start_date"),
                    "expected_end_date": attrs.get("expected_end_date"),
                    "current_program_month": attrs.get("current_program_month") or months_elapsed,
                    "months_elapsed": months_elapsed,
                    "months_remaining": max(0, 24 - (months_elapsed or 0)),
                }
            )
        return {
            "advisor": merged.get("advisor", []),
            "enrollments": enrollments,
            "programs": merged.get("programs", []),
            "goals": merged.get("goals", []),
            "kpis": merged.get("kpis", []),
        }

    # -- AGP-002/003: milestone timeline with KPI measurements --

    def milestone_timeline(self, enrollment_id: str) -> dict:
        result = self.graph.run_query("get_agp_milestone_timeline", {"enrollment_id": enrollment_id})
        merged: dict = {}
        for entry in result.get("results", []):
            merged.update(entry)

        milestones_by_id = {m["v_id"]: _attrs(m) for m in merged.get("milestones", [])}
        timeline = []
        for progress in merged.get("progress", []):
            attrs = _attrs(progress)
            due = _parse_date(attrs.get("due_date"))
            days_remaining = (due - self.today).days if due else None
            timeline.append(
                {
                    "milestone_progress_id": progress.get("v_id"),
                    "due_date": attrs.get("due_date"),
                    "days_remaining": days_remaining,
                    "status": attrs.get("status"),
                    "attainment_pct": attrs.get("attainment_pct"),
                    "risk_score": attrs.get("risk_score"),
                }
            )
        timeline.sort(key=lambda m: str(m["due_date"]))
        measurements = [
            {
                "measurement_id": m.get("v_id"),
                **{k: _attrs(m).get(k) for k in ("target_value", "actual_value", "attainment_pct", "status", "measured_at")},
            }
            for m in merged.get("measurements", [])
        ]
        return {
            "enrollment": merged.get("enrollment", []),
            "milestone_months": MILESTONE_MONTHS,
            "timeline": timeline,
            "milestones": list(milestones_by_id.values()),
            "measurements": measurements,
            "kpis": merged.get("kpis", []),
        }

    # -- AGP-002/003: per-KPI Target vs Current scorecard with history --

    def kpi_scorecard(self, advisor_id: str) -> dict:
        """Per-KPI Target vs Current, attainment %, on/off-track status and a time
        history, traversed advisor -> enrollment -> milestone_progress ->
        kpi_measurement -> kpi. Backed by real phx_dm_agp_kpi_measurement rows via
        GQ-055 get_agp_kpi_scorecard (run_query); the direct store traversal below
        survives only as the logged fallback."""
        kpi_rows: dict[str, dict] = {}
        results = run_catalog_query(self.graph, "get_agp_kpi_scorecard", {"advisor_id": advisor_id})
        rows = None
        if results is not None:
            for entry in results:
                if entry.get("kpi_measurement_rows") is not None:
                    rows = entry["kpi_measurement_rows"]
                    break
            if rows is None:
                logger.warning(
                    "get_agp_kpi_scorecard returned no kpi_measurement_rows entry for %s — "
                    "falling back to local store traversal", advisor_id,
                )
        if rows is not None:
            for raw in rows:
                m = raw.get("attributes", raw)
                kid = str(m.get("kpi_id") or "")
                if not kid:
                    continue  # measurement without a measured KPI — mirrors the store path's skip
                month = m.get("milestone_month") or None
                row = kpi_rows.setdefault(kid, {
                    "kpi_id": kid,
                    "kpi_name": m.get("kpi_name") or kid,
                    "unit": m.get("unit") or None,
                    "direction": m.get("direction") or None,
                    "history": [],
                })
                row["history"].append({
                    "label": f"M{month}" if month else str(m.get("measured_at"))[:7],
                    "month": int(month or 0),
                    "target": float(m.get("target_value") or 0),
                    "actual": float(m.get("actual_value") or 0),
                    "attainment_pct": float(m.get("attainment_pct") or 0),
                    "status": m.get("status"),
                    "measured_at": m.get("measured_at"),
                })
        else:
            store = graph_fallback_store(self.graph)

            def vattrs(vtype: str, vid: str) -> dict:
                return store.vertex(vtype, vid) or {}

            for enr in store.out_ids("phx_dm_advisor_has_agp_enrollment", advisor_id):
                for prog in store.out_ids("phx_dm_enrollment_has_milestone_progress", enr):
                    ms_ids = store.out_ids("phx_dm_progress_for_milestone", prog)
                    month = vattrs("phx_dm_agp_milestone", ms_ids[0]).get("milestone_month") if ms_ids else None
                    for meas in store.out_ids("phx_dm_progress_has_kpi_measurement", prog):
                        m = vattrs("phx_dm_agp_kpi_measurement", meas)
                        kpi_ids = store.out_ids("phx_dm_measurement_for_kpi", meas)
                        if not kpi_ids:
                            continue
                        kid = kpi_ids[0]
                        kdef = vattrs("phx_dm_kpi", kid)
                        row = kpi_rows.setdefault(kid, {
                            "kpi_id": kid,
                            "kpi_name": kdef.get("kpi_name", kid),
                            "unit": kdef.get("unit"),
                            "direction": kdef.get("direction"),
                            "history": [],
                        })
                        row["history"].append({
                            "label": f"M{month}" if month else str(m.get("measured_at"))[:7],
                            "month": int(month or 0),
                            "target": float(m.get("target_value") or 0),
                            "actual": float(m.get("actual_value") or 0),
                            "attainment_pct": float(m.get("attainment_pct") or 0),
                            "status": m.get("status"),
                            "measured_at": m.get("measured_at"),
                        })

        scorecard = []
        for row in kpi_rows.values():
            row["history"].sort(key=lambda h: (h["month"], str(h["measured_at"])))
            latest = row["history"][-1] if row["history"] else {}
            scorecard.append({
                "kpi_id": row["kpi_id"],
                "kpi_name": row["kpi_name"],
                "unit": row["unit"],
                "direction": row["direction"],
                "target": latest.get("target"),
                "current": latest.get("actual"),
                "attainment_pct": round(float(latest.get("attainment_pct") or 0), 1),
                "status": latest.get("status"),
                "history": row["history"],
            })
        scorecard.sort(key=lambda r: r["kpi_name"])
        return {"advisor_id": advisor_id, "scorecard": scorecard}

    # -- AGP-004: on/off-track score + band + explanation --

    def track_status(self, advisor_id: str) -> dict:
        """Risk score from KPI attainment, time remaining and CRM execution.
        Returns score (0-100, higher = more at risk), band and explanation —
        every component preserved for explainability."""
        summary = self.enrollment_summary(advisor_id)
        if not summary["enrollments"]:
            return {"advisor_id": advisor_id, "enrolled": False}
        enrollment = summary["enrollments"][0]
        timeline = self.milestone_timeline(enrollment["enrollment_id"])

        # Component 1 — attainment gap (weight 0.45): how far current-milestone
        # attainment is below 100%, using the nearest not-yet-overdue milestone.
        open_milestones = [m for m in timeline["timeline"] if (m["days_remaining"] or 0) >= 0]
        current = open_milestones[0] if open_milestones else (timeline["timeline"][-1] if timeline["timeline"] else None)
        attainment = float(current["attainment_pct"] or 0) if current else 0.0
        attainment_gap = max(0.0, 100.0 - attainment)

        # Component 2 — time pressure (weight 0.25): low days-remaining amplifies risk.
        days_remaining = (current or {}).get("days_remaining")
        if days_remaining is None:
            time_pressure = 50.0
        else:
            time_pressure = max(0.0, min(100.0, (90 - days_remaining) / 90 * 100))

        # Component 3 — CRM execution (weight 0.30): overdue + incomplete work items.
        crm = self.graph.run_query("get_agp_crm_work_summary", {"advisor_id": advisor_id})
        crm_merged: dict = {}
        for entry in crm.get("results", []):
            crm_merged.update(entry)
        total_items = 0
        overdue_or_pending = 0
        for row in crm_merged.get("crm_work_summary", []):
            count = int(row.get("item_count") or 0)
            total_items += count
            if str(row.get("status", "")).upper() in {"PENDING", "OVERDUE", "OPEN"}:
                overdue_or_pending += count
        crm_execution_risk = (overdue_or_pending / total_items * 100) if total_items else 50.0

        score = round(attainment_gap * 0.45 + time_pressure * 0.25 + crm_execution_risk * 0.30, 1)
        band = _band(score, TRACK_BANDS)
        explanation = (
            f"Milestone attainment is {attainment:.0f}% (gap contributes {attainment_gap * 0.45:.0f} pts). "
            f"{'No open milestone.' if days_remaining is None else f'{days_remaining} days remain to the next milestone'}"
            f" (time pressure contributes {time_pressure * 0.25:.0f} pts). "
            f"{overdue_or_pending} of {total_items} CRM work items are pending or overdue "
            f"(execution contributes {crm_execution_risk * 0.30:.0f} pts)."
        )
        return {
            "advisor_id": advisor_id,
            "enrolled": True,
            "enrollment_id": enrollment["enrollment_id"],
            "score": score,
            "band": band,
            "severity": _band(score, SEVERITY_BANDS),
            "components": {
                "attainment_gap": round(attainment_gap, 1),
                "time_pressure": round(time_pressure, 1),
                "crm_execution_risk": round(crm_execution_risk, 1),
                "weights": {"attainment_gap": 0.45, "time_pressure": 0.25, "crm_execution_risk": 0.30},
            },
            "explanation": explanation,
            "current_milestone": current,
        }

    # -- AGP-005: coaching and review history --

    def coaching_history(self, advisor_id: str) -> dict:
        result = self.graph.run_query("get_agp_coaching_history", {"advisor_id": advisor_id})
        merged: dict = {}
        for entry in result.get("results", []):
            merged.update(entry)
        sessions = sorted(
            (
                {"session_id": c.get("v_id"), **_attrs(c)}
                for c in merged.get("coaching", []) + merged.get("enrollment_coaching", [])
            ),
            key=lambda s: str(s.get("session_date")),
            reverse=True,
        )
        reviews = sorted(
            (
                {"review_id": r.get("v_id"), **_attrs(r)}
                for r in merged.get("reviews", []) + merged.get("enrollment_reviews", [])
            ),
            key=lambda r: str(r.get("review_date")),
            reverse=True,
        )
        # de-duplicate items reachable via both advisor and enrollment paths
        seen: set[str] = set()
        sessions = [s for s in sessions if not (s["session_id"] in seen or seen.add(s["session_id"]))]
        seen.clear()
        reviews = [r for r in reviews if not (r["review_id"] in seen or seen.add(r["review_id"]))]
        return {"advisor_id": advisor_id, "coaching_sessions": sessions, "manager_reviews": reviews}

    # -- AGP-006: cohort comparison --

    def cohort_summary(self, program_id: str, cohort: str, scope_type: str, scope_id: str) -> dict:
        result = self.graph.run_query(
            "get_agp_program_cohort_summary",
            {"program_id": program_id, "cohort": cohort, "scope_type": scope_type, "scope_id": scope_id},
        )
        merged: dict = {}
        for entry in result.get("results", []):
            merged.update(entry)
        summary = merged.get("milestone_summary", [])
        for row in summary:
            count = row.get("progress_count") or 0
            row["avg_attainment_pct"] = round(row.get("attainment_sum", 0) / count, 1) if count else None
            row["avg_risk_score"] = round(row.get("risk_sum", 0) / count, 1) if count else None
        return {
            "program_id": program_id,
            "cohort": cohort,
            "scope": {"scope_type": scope_type, "scope_id": scope_id},
            "enrollment_count": merged.get("enrollment_count", 0),
            "milestone_summary": summary,
        }
