from __future__ import annotations

import logging
from datetime import datetime, timedelta

from app.graph.client import get_graph_client
from app.graph.queries.common import (
    resolve_scope_advisor_ids_graph,
    run_catalog_query,
    scope_advisor_placements,
)
from app.features.snapshot_store import SnapshotStore

logger = logging.getLogger(__name__)

# Wide DATETIME bounds for GQ-007 (required params; cover the full data range).
_DATE_MIN = "1900-01-01 00:00:00"
_DATE_MAX = "2100-01-01 00:00:00"

# AGP-004 status bands on the 0-100 agp_risk_score scale (higher = worse),
# reused from app.agp.service so scope rollups classify advisors the same way
# individual AGP pages do — never redefined per-page.
TRACK_BANDS = [
    (0, 39, "on_track"),
    (40, 69, "attention"),
    (70, 84, "urgent"),
    (85, 100, "critical"),
]

# child scope type + the edge whose in_ids gives the children of a parent id,
# plus the child vertex type and its display-name attribute. Drives one level of
# drill-down (Firm->Divisions->Regions->Markets->Advisors).
_CHILDREN = {
    "FIRM": ("Division", "phx_dm_division_in_firm", "phx_dm_division", "division_name"),
    "DIVISION": ("Region", "phx_dm_region_in_division", "phx_dm_region", "region_name"),
    "REGION": ("Market", "phx_dm_market_in_region", "phx_dm_market", "market_name"),
    "MARKET": ("Advisor", "phx_dm_advisor_in_market", "phx_dm_advisor", "advisor_name"),
}


def _band(score: float) -> str:
    # Upper-bound thresholds so fractional scores in the old gaps (e.g. 39.9, 69.5) classify
    # correctly instead of falling through to "critical". <40 on_track / <70 attention / <85 urgent.
    if score < 40:
        return "on_track"
    if score < 70:
        return "attention"
    if score < 85:
        return "urgent"
    return "critical"


class ScopeRollupService:
    """Aggregates each advisor's REAL latest feature snapshot up to any hierarchy
    scope (Firm/Division/Region/Market/Advisor). Every rollup number is a sum or
    mean over the resolved advisors' actual snapshot values — no hardcoded
    firm-wide figures (CLAUDE.md 5B item 3). The same page adapts what it shows to
    the selected scope by calling this with the breadcrumb's scope_type/scope_id."""

    def __init__(self) -> None:
        self._graph = get_graph_client()
        self._store = self._graph.store  # logged fallback path only — reads go via run_query
        self._snaps = SnapshotStore()

    def _features(self, advisor_id: str) -> dict:
        snap = self._snaps.latest_for_entity("ADVISOR", advisor_id)
        return (snap or {}).get("features", {}) if snap else {}

    def _name(self, vtype: str, vid: str, attr: str) -> str:
        return str((self._store.vertex(vtype, vid) or {}).get(attr) or vid)

    @staticmethod
    def _num(f: dict, key: str) -> float:
        v = f.get(key)
        return float(v) if v is not None else 0.0

    def _aggregate(self, advisor_ids: list[str]) -> dict:
        """Sum/mean the snapshot metrics over a set of advisors."""
        revenue = aum = nnm_annual = managed = 0.0
        goal_sum = risk_sum = 0.0
        counted = 0
        status = {"on_track": 0, "attention": 0, "urgent": 0, "critical": 0}
        for advisor_id in advisor_ids:
            f = self._features(advisor_id)
            if not f:
                continue
            counted += 1
            rev = self._num(f, "revenue_ltm")
            revenue += rev
            aum += self._num(f, "aum_total")
            nnm_annual += self._num(f, "nnm_3m") * 4.0
            managed += rev * self._num(f, "managed_revenue_ratio")
            goal_sum += self._num(f, "kpi_on_track_ratio") * 100.0
            risk = self._num(f, "agp_risk_score")
            risk_sum += risk
            status[_band(risk)] += 1
        return {
            "advisor_count": len(advisor_ids),
            "advisors_with_data": counted,
            "revenue_ltm": round(revenue, 2),
            "aum_total": round(aum, 2),
            "nnm_annualized": round(nnm_annual, 2),
            "managed_revenue": round(managed, 2),
            "avg_goal_attainment": round(goal_sum / counted, 1) if counted else 0.0,
            "avg_agp_risk_score": round(risk_sum / counted, 1) if counted else 0.0,
            "status_distribution": status,
        }

    def _child_breakdown(self, scope_type: str, scope_id: str,
                         placements: dict[str, dict] | None) -> list[dict]:
        """One level of drill-down: each immediate child's own rollup. Firm->per
        division, Division->per region, etc. Market->per advisor. Advisor has no
        children. Powers scope-aware bar/donut charts on the leadership pages.
        Children come from the GQ-053 placements of the scope's advisors; direct
        store traversal only on the logged fallback path."""
        st = scope_type.upper()
        if st == "ADVISOR" or st not in _CHILDREN:
            return []
        child_type, edge, child_vtype, name_attr = _CHILDREN[st]
        rows = []
        if placements is not None:
            child_key = {"FIRM": "division", "DIVISION": "region", "REGION": "market"}.get(st)
            groups: dict[str, dict] = {}
            for aid, p in placements.items():
                if child_key is None:  # MARKET -> children are the advisors themselves
                    cid, label = aid, str(p.get("advisor_name") or aid)
                else:
                    cid = str(p.get(f"{child_key}_id") or "")
                    label = str(p.get(f"{child_key}_name") or cid)
                if not cid:
                    continue
                g = groups.setdefault(cid, {"label": label, "advisors": []})
                g["advisors"].append(aid)
            for cid in sorted(groups):
                g = groups[cid]
                agg = self._aggregate(g["advisors"])
                rows.append({
                    "scope_type": child_type,
                    "scope_id": cid,
                    "label": g["label"],
                    "advisor_count": agg["advisor_count"],
                    "revenue_ltm": agg["revenue_ltm"],
                    "aum_total": agg["aum_total"],
                    "avg_goal_attainment": agg["avg_goal_attainment"],
                })
            return rows
        logger.warning(
            "child breakdown for %s/%s using local store traversal fallback", st, scope_id,
        )
        for child_id in sorted(self._store.in_ids(edge, scope_id)):
            child_advisors = resolve_scope_advisor_ids_graph(self._graph, child_type, child_id)
            agg = self._aggregate(child_advisors)
            rows.append({
                "scope_type": child_type,
                "scope_id": child_id,
                "label": self._name(child_vtype, child_id, name_attr),
                "advisor_count": agg["advisor_count"],
                "revenue_ltm": agg["revenue_ltm"],
                "aum_total": agg["aum_total"],
                "avg_goal_attainment": agg["avg_goal_attainment"],
            })
        return rows

    def _top_advisors(self, scope_type: str, scope_id: str, advisor_ids: list[str],
                      placements: dict[str, dict] | None, limit: int = 8, ascending: bool = False,
                      start_date: str | None = None, end_date: str | None = None) -> list[dict]:
        """Top/bottom advisors ranked by REAL transaction revenue in the selected
        period window via GQ-007 get_top_bottom_advisors — the ranking spans the
        full advisor universe of the scope on the live graph, so top-N and
        bottom-N are disjoint regardless of local snapshot coverage. Display
        fields (revenue_ltm, AUM, AGP status) are enriched from each advisor's
        latest feature snapshot; snapshot-based ranking remains ONLY as the
        logged fallback."""
        direction = "BOTTOM" if ascending else "TOP"
        results = run_catalog_query(
            self._graph,
            "get_top_bottom_advisors",
            {"scope_type": scope_type, "scope_id": str(scope_id),
             "start_date": start_date or _DATE_MIN, "end_date": end_date or _DATE_MAX,
             "direction": direction, "result_limit": limit},
        )
        ranked = None
        if results is not None:
            for entry in results:
                rows = entry.get("bottom_advisors" if ascending else "top_advisors")
                if rows is not None:
                    ranked = rows
                    break
        if ranked is None:
            logger.warning(
                "get_top_bottom_advisors unavailable for %s/%s — falling back to snapshot ranking",
                scope_type, scope_id,
            )
            return self._top_advisors_from_snapshots(advisor_ids, limit, ascending)

        picked = []
        for row in ranked:
            # tier 2 prints vset rows ({v_id, attributes}); the mock returns flat dicts
            r = row.get("attributes", row) if isinstance(row, dict) else {}
            aid = str(r.get("advisor_id") or row.get("v_id") or "")
            if not aid:
                continue
            f = self._features(aid)
            kpi = f.get("kpi_on_track_ratio") if f else None
            risk = f.get("agp_risk_score") if f else None
            name = (
                r.get("advisor_name")
                or ((placements or {}).get(aid) or {}).get("advisor_name")
                or self._name("phx_dm_advisor", aid, "advisor_name")
            )
            period_rev = round(float(r.get("revenue") or 0.0), 2)
            picked.append({
                "advisor_id": aid,
                "advisor_name": str(name),
                "revenue_ltm": round(self._num(f, "revenue_ltm"), 2) if f else period_rev,
                "period_revenue": period_rev,
                "aum_total": round(self._num(f, "aum_total"), 2) if f else 0.0,
                "goal_attainment": round(float(kpi) * 100.0, 1) if kpi is not None else None,
                "agp_risk_score": round(float(risk), 1) if risk is not None else None,
                "status": _band(float(risk)) if risk is not None else "n/a",
            })
        for r in picked:
            if ascending:
                if r["status"] in ("attention", "urgent", "critical"):
                    r["reason"] = f"AGP {r['status'].replace('_', ' ')} (risk {r['agp_risk_score']})"
                else:
                    r["reason"] = "Lowest revenue in scope for the selected period"
            else:
                r["reason"] = "Highest revenue in scope for the selected period"
        return picked

    def _top_advisors_from_snapshots(self, advisor_ids: list[str], limit: int = 8, ascending: bool = False) -> list[dict]:
        rows = []
        for advisor_id in advisor_ids:
            f = self._features(advisor_id)
            if not f:
                continue
            # AGP goal/risk are None for advisors not enrolled in the growth program — render
            # those as absent ("—" client-side), never as a fabricated 0% / 0 / on-track.
            kpi = f.get("kpi_on_track_ratio")
            risk = f.get("agp_risk_score")
            rows.append({
                "advisor_id": advisor_id,
                "advisor_name": self._name("phx_dm_advisor", advisor_id, "advisor_name"),
                "revenue_ltm": round(self._num(f, "revenue_ltm"), 2),
                "aum_total": round(self._num(f, "aum_total"), 2),
                "goal_attainment": round(float(kpi) * 100.0, 1) if kpi is not None else None,
                "agp_risk_score": round(float(risk), 1) if risk is not None else None,
                "status": _band(float(risk)) if risk is not None else "n/a",
            })
        rows.sort(key=lambda r: r["revenue_ltm"], reverse=not ascending)
        picked = rows[:limit]
        # Stated reason per advisor (9.5: top AND bottom, each with a why).
        for r in picked:
            if ascending:
                if r["status"] in ("attention", "urgent", "critical"):
                    r["reason"] = f"AGP {r['status'].replace('_', ' ')} (risk {r['agp_risk_score']})"
                else:
                    r["reason"] = "Lowest LTM revenue in scope"
            else:
                r["reason"] = "Highest LTM revenue in scope"
        return picked

    def _disjoint_top_bottom(self, scope_type: str, scope_id: str, advisor_ids: list[str],
                             placements: dict[str, dict] | None,
                             start_date: str | None, end_date: str | None) -> dict:
        """Top/bottom lists with the invariant that no advisor appears in both.
        When the scope holds fewer advisors than two full lists, the ranked
        universe is split in half (top half / bottom half) instead of showing
        the same advisors twice."""
        top = self._top_advisors(scope_type, scope_id, advisor_ids, placements,
                                 start_date=start_date, end_date=end_date)
        bottom = self._top_advisors(scope_type, scope_id, advisor_ids, placements,
                                    ascending=True, start_date=start_date, end_date=end_date)
        top_ids = {r["advisor_id"] for r in top}
        if any(r["advisor_id"] in top_ids for r in bottom):
            half = max(1, len(advisor_ids) // 2)
            top = top[:half]
            top_ids = {r["advisor_id"] for r in top}
            bottom = [r for r in bottom if r["advisor_id"] not in top_ids][:half]
        return {"top_advisors": top, "bottom_advisors": bottom}

    def _comparison(self, scope_type: str, scope_id: str) -> tuple[dict, list[str]]:
        """Current trailing-12mo revenue vs the prior 12mo, from the 36-month trend — powers the
        prior-year delta badges (9.5). Reuses the same monthly aggregation the Revenue page uses.
        Also returns the full list of data months so the caller can derive the
        selected-period ranking window without a second pass."""
        from app.revenue.analytics import RevenueAnalyticsService
        try:
            trend = RevenueAnalyticsService().analytics(scope_type, scope_id).get("monthly_trend", [])
            revs = [float(m.get("revenue", 0) or 0) for m in trend]
            months = [str(m.get("month") or "") for m in trend]
        except Exception:
            revs, months = [], []
        cur = round(sum(revs[-12:]), 2)
        prior = round(sum(revs[-24:-12]), 2)
        pct = round(((cur - prior) / prior * 100.0), 1) if prior else 0.0
        return {"revenue_current_12m": cur, "revenue_prior_12m": prior, "revenue_change_pct": pct}, months

    @staticmethod
    def _period_window(period: str | None, months: list[str]) -> tuple[str | None, str | None]:
        """(start_date, end_date) DATETIME bounds for the Time Period selection,
        anchored to the scope's real data months — the ranking window GQ-007 uses."""
        p = (period or "ALL").upper()
        if p in ("ALL", "ALLTIME", "") or not months:
            return None, None
        from app.revenue.analytics import RevenueAnalyticsService
        cur = RevenueAnalyticsService._current_months(months, p)
        if not cur:
            return None, None
        mx = max(cur)
        y, m = int(mx[:4]), int(mx[5:7])
        end = (datetime(y + (1 if m == 12 else 0), 1 if m == 12 else m + 1, 1)
               - timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")
        return f"{min(cur)}-01 00:00:00", end

    def summary(self, scope_type: str = "FIRM", scope_id: str = "F001",
                period: str | None = None) -> dict:
        st = (scope_type or "FIRM").upper()
        advisor_ids = resolve_scope_advisor_ids_graph(self._graph, st, scope_id)
        placements = scope_advisor_placements(self._graph, st, scope_id)
        agg = self._aggregate(advisor_ids)
        comparison, months = self._comparison(st, scope_id)
        start_date, end_date = self._period_window(period, months)
        return {
            "scope_type": st,
            "scope_id": scope_id,
            "totals": agg,
            "comparison": comparison,
            "child_breakdown": self._child_breakdown(st, scope_id, placements),
            **self._disjoint_top_bottom(st, scope_id, advisor_ids, placements, start_date, end_date),
            "evidence": {
                "source": "per-advisor latest feature snapshots (SnapshotStore), summed/averaged",
                "advisor_ids_resolved": len(advisor_ids),
                "advisor_ids_sample": advisor_ids[:10],
                "computation": (
                    "revenue_ltm/aum_total/managed_revenue = Σ advisor snapshot values; "
                    "nnm_annualized = Σ nnm_3m×4; avg_goal_attainment = mean(kpi_on_track_ratio×100); "
                    "status = agp_risk_score banded per AGP-004 TRACK_BANDS"
                ),
            },
        }
