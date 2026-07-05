from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.graph.client import GraphClient, get_graph_client


def _attrs(vertex: dict) -> dict:
    return vertex.get("attributes", {})


def _parse_date(value: Any) -> date | None:
    text = str(value or "")[:10]
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


class CrmService:
    """CRM domain logic (CRM-001..005): first-class leads/referrals/opportunities
    with status/age/due/conversion analytics, distinct from AI opportunities
    (CRM-003). Everything computed from graph data via GraphClient."""

    def __init__(self, graph: GraphClient | None = None, today: date | None = None) -> None:
        self.graph = graph or get_graph_client()
        self.today = today or date.today()

    def _merged(self, query: str, params: dict) -> dict:
        result = self.graph.run_query(query, params)
        merged: dict = {}
        for entry in result.get("results", []):
            merged.update(entry)
        return merged

    def _enrich_work_item(self, vertex: dict, id_field: str, created_field: str) -> dict:
        attrs = _attrs(vertex)
        due = _parse_date(attrs.get("due_date"))
        created = _parse_date(attrs.get(created_field))
        status = str(attrs.get("status", "")).upper()
        overdue = bool(due and due < self.today and status not in {"COMPLETED", "CONVERTED", "CLOSED"})
        return {
            "id": vertex.get("v_id"),
            **attrs,
            "age_days": (self.today - created).days if created else None,
            "days_to_due": (due - self.today).days if due else None,
            "overdue": overdue,
        }

    # -- CRM-001: leads --

    def leads(self, advisor_id: str, status: str = "ALL", limit: int = 50) -> dict:
        merged = self._merged("get_crm_leads", {"advisor_id": advisor_id, "status": status, "result_limit": limit})
        items = [self._enrich_work_item(lead, "lead_id", "created_date") for lead in merged.get("leads", [])]
        return {"advisor_id": advisor_id, "leads": items, "summary": self._work_item_stats(items)}

    # -- CRM-002: referrals --

    def referrals(self, advisor_id: str, status: str = "ALL", limit: int = 50) -> dict:
        merged = self._merged("get_crm_referrals", {"advisor_id": advisor_id, "status": status, "result_limit": limit})
        items = [self._enrich_work_item(r, "referral_id", "received_date") for r in merged.get("referrals", [])]
        return {"advisor_id": advisor_id, "referrals": items, "summary": self._work_item_stats(items)}

    @staticmethod
    def _work_item_stats(items: list[dict]) -> dict:
        total = len(items)
        completed = sum(1 for i in items if str(i.get("status", "")).upper() == "COMPLETED")
        converted = sum(1 for i in items if i.get("converted_flag"))
        overdue = sum(1 for i in items if i.get("overdue"))
        pending = sum(1 for i in items if str(i.get("status", "")).upper() in {"PENDING", "OPEN", "NEW"})
        return {
            "total": total,
            "pending": pending,
            "completed": completed,
            "converted": converted,
            "overdue": overdue,
            "completion_rate_pct": round(completed / total * 100, 1) if total else 0.0,
            "conversion_rate_pct": round(converted / total * 100, 1) if total else 0.0,
            "estimated_value_total": round(sum(float(i.get("estimated_value") or 0) for i in items), 2),
        }

    # -- CRM-003: pipeline opportunities (explicitly CRM, not AI) --

    def opportunities(self, advisor_id: str, status: str = "ALL", limit: int = 50) -> dict:
        merged = self._merged(
            "get_crm_opportunities", {"advisor_id": advisor_id, "status": status, "result_limit": limit}
        )
        items = []
        for opp in merged.get("opportunities", []):
            attrs = _attrs(opp)
            close = _parse_date(attrs.get("expected_close_date"))
            items.append(
                {
                    "id": opp.get("v_id"),
                    "opportunity_kind": "CRM",  # CRM-003: never confuse with AI opportunities
                    **attrs,
                    "weighted_amount": round(float(attrs.get("amount") or 0) * float(attrs.get("probability") or 0), 2),
                    "days_to_close": (close - self.today).days if close else None,
                }
            )
        return {"advisor_id": advisor_id, "opportunities": items}

    def pipeline_by_stage(self, advisor_id: str) -> dict:
        merged = self._merged("get_crm_pipeline_by_stage", {"advisor_id": advisor_id})
        return {"advisor_id": advisor_id, "pipeline_by_stage": merged.get("pipeline_by_stage", [])}

    # -- CRM-004: consolidated AGP CRM tracking metrics --

    def work_summary(self, advisor_id: str) -> dict:
        merged = self._merged("get_agp_crm_work_summary", {"advisor_id": advisor_id})
        leads = self.leads(advisor_id)
        referrals = self.referrals(advisor_id)
        return {
            "advisor_id": advisor_id,
            "work_summary": merged.get("crm_work_summary", []),
            "pipeline": merged.get("crm_pipeline", []),
            "lead_summary": leads["summary"],
            "referral_summary": referrals["summary"],
        }

    # -- CRM-005: CRM-derived feature inputs for the AI pipeline --

    def feature_inputs(self, advisor_id: str) -> dict:
        """CRM signals consumed by feature engineering (Phase 5): age, status,
        follow-ups, pipeline and activity, with the item ids as lineage."""
        leads = self.leads(advisor_id)
        referrals = self.referrals(advisor_id)
        pipeline = self.pipeline_by_stage(advisor_id)["pipeline_by_stage"]
        open_pipeline = [p for p in pipeline if str(p.get("stage", "")).upper() not in {"CLOSED_WON", "CLOSED_LOST"}]
        features = {
            "crm_lead_total": leads["summary"]["total"],
            "crm_lead_overdue": leads["summary"]["overdue"],
            "crm_lead_conversion_rate_pct": leads["summary"]["conversion_rate_pct"],
            "crm_referral_total": referrals["summary"]["total"],
            "crm_referral_overdue": referrals["summary"]["overdue"],
            "crm_referral_conversion_rate_pct": referrals["summary"]["conversion_rate_pct"],
            "crm_open_pipeline_amount": round(sum(float(p.get("pipeline_amount") or 0) for p in open_pipeline), 2),
            "crm_open_pipeline_weighted": round(sum(float(p.get("weighted_amount") or 0) for p in open_pipeline), 2),
            "crm_open_opportunity_count": sum(int(p.get("opportunity_count") or 0) for p in open_pipeline),
        }
        lineage = {
            "lead_ids": [i["id"] for i in leads["leads"]],
            "referral_ids": [i["id"] for i in referrals["referrals"]],
            "pipeline_stages": [p.get("stage") for p in pipeline],
        }
        return {"advisor_id": advisor_id, "features": features, "lineage": lineage}

    # -- CRM activities: meetings/calls/emails/reviews/follow-ups (real records) --

    def activities(self, advisor_id: str, limit: int = 60) -> dict:
        """CRM activities for an advisor with the household they were with, a weekly
        breakdown by type, recent meetings and per-activity notes — read straight
        from phx_dm_crm_activity via activity_for_advisor / activity_for_household."""
        store = self.graph.store
        rows: list[dict] = []
        for aid in store.in_ids("phx_dm_activity_for_advisor", advisor_id):
            a = store.vertex("phx_dm_crm_activity", aid) or {}
            hh_ids = store.out_ids("phx_dm_activity_for_household", aid)
            with_name = None
            if hh_ids:
                with_name = (store.vertex("phx_dm_household", hh_ids[0]) or {}).get("household_name")
            rows.append({
                "activity_id": a.get("activity_id", aid),
                "activity_type": a.get("activity_type"),
                "activity_date": a.get("activity_date"),
                "status": a.get("status"),
                "subject": a.get("subject"),
                "with": with_name or "—",
                "notes_summary": a.get("notes_summary"),
                "next_action": a.get("next_action"),
                "next_action_date": a.get("next_action_date"),
                "sentiment": a.get("sentiment"),
            })
        rows.sort(key=lambda r: str(r.get("activity_date") or ""), reverse=True)
        rows = rows[:limit]

        # counts by type (icon-labelled row) + "this week" window (activity or next
        # action within ±7 days of today)
        by_type: dict[str, int] = {}
        this_week: dict[str, int] = {}
        for r in rows:
            t = str(r.get("activity_type") or "OTHER")
            by_type[t] = by_type.get(t, 0) + 1
            for d in (_parse_date(r.get("activity_date")), _parse_date(r.get("next_action_date"))):
                if d and abs((d - self.today).days) <= 7:
                    this_week[t] = this_week.get(t, 0) + 1
                    break

        meetings = [r for r in rows if str(r.get("activity_type")).upper() in {"MEETING", "REVIEW"}][:10]
        upcoming = sorted(
            (r for r in rows if _parse_date(r.get("next_action_date")) and _parse_date(r["next_action_date"]) >= self.today),
            key=lambda r: str(r.get("next_action_date")),
        )[:8]
        return {
            "advisor_id": advisor_id,
            "activities": rows,
            "by_type": by_type,
            "this_week": this_week,
            "recent_meetings": meetings,
            "upcoming": upcoming,
        }
