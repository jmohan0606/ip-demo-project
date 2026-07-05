from __future__ import annotations

from app.graph.client import get_graph_client
from app.graph.queries.common import resolve_scope_advisor_ids
from app.features.snapshot_store import SnapshotStore

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
    for low, high, label in TRACK_BANDS:
        if low <= score <= high:
            return label
    return TRACK_BANDS[-1][2]


class ScopeRollupService:
    """Aggregates each advisor's REAL latest feature snapshot up to any hierarchy
    scope (Firm/Division/Region/Market/Advisor). Every rollup number is a sum or
    mean over the resolved advisors' actual snapshot values — no hardcoded
    firm-wide figures (CLAUDE.md 5B item 3). The same page adapts what it shows to
    the selected scope by calling this with the breadcrumb's scope_type/scope_id."""

    def __init__(self) -> None:
        self._store = get_graph_client().store
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

    def _child_breakdown(self, scope_type: str, scope_id: str) -> list[dict]:
        """One level of drill-down: each immediate child's own rollup. Firm->per
        division, Division->per region, etc. Market->per advisor. Advisor has no
        children. Powers scope-aware bar/donut charts on the leadership pages."""
        st = scope_type.upper()
        if st == "ADVISOR" or st not in _CHILDREN:
            return []
        child_type, edge, child_vtype, name_attr = _CHILDREN[st]
        rows = []
        for child_id in sorted(self._store.in_ids(edge, scope_id)):
            child_advisors = resolve_scope_advisor_ids(self._store, child_type, child_id)
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

    def _top_advisors(self, advisor_ids: list[str], limit: int = 8) -> list[dict]:
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
        rows.sort(key=lambda r: r["revenue_ltm"], reverse=True)
        return rows[:limit]

    def summary(self, scope_type: str = "FIRM", scope_id: str = "F001") -> dict:
        st = (scope_type or "FIRM").upper()
        advisor_ids = resolve_scope_advisor_ids(self._store, st, scope_id)
        agg = self._aggregate(advisor_ids)
        return {
            "scope_type": st,
            "scope_id": scope_id,
            "totals": agg,
            "child_breakdown": self._child_breakdown(st, scope_id),
            "top_advisors": self._top_advisors(advisor_ids),
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
