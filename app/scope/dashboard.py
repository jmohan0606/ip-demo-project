from __future__ import annotations

from app.graph.client import get_graph_client
from app.graph.queries.common import resolve_scope_advisor_ids
from app.features.snapshot_store import SnapshotStore
from app.scope.rollup import ScopeRollupService
from app.revenue.analytics import RevenueAnalyticsService


class ScopeDashboardService:
    """Composes everything the Executive Dashboard (12.1) needs into ONE
    period-aware, scope-aware payload: the rollup totals + status + top/bottom
    advisors (snapshot-based), the period-windowed revenue trend / product-category
    / channel / geography / YoY drivers (RevenueAnalyticsService), top & bottom
    markets, a peer benchmark, and a headline revenue figure whose delta respects
    the Compare-To control (Prior Year | Prior Period | Peer Benchmark | None).
    Every number is a real sum/mean over resolved advisors — no hardcoded totals."""

    def __init__(self) -> None:
        self._store = get_graph_client().store
        self._snaps = SnapshotStore()

    # ---- helpers -----------------------------------------------------------
    def _rev_ltm(self, advisor_id: str) -> float:
        snap = self._snaps.latest_for_entity("ADVISOR", advisor_id)
        f = (snap or {}).get("features", {}) if snap else {}
        v = f.get("revenue_ltm")
        return float(v) if v is not None else 0.0

    def _name(self, vtype: str, vid: str, attr: str) -> str:
        return str((self._store.vertex(vtype, vid) or {}).get(attr) or vid)

    def _firm_id(self) -> str:
        firms = list(self._store.all_vertices("phx_dm_firm").keys())
        return firms[0] if firms else "F001"

    def _markets_under(self, scope_type: str, scope_id: str) -> list[str]:
        s = self._store
        st = scope_type.upper()
        if st == "FIRM":
            ids: list[str] = []
            for d in s.in_ids("phx_dm_division_in_firm", scope_id):
                for r in s.in_ids("phx_dm_region_in_division", d):
                    ids.extend(s.in_ids("phx_dm_market_in_region", r))
            return ids
        if st == "DIVISION":
            ids = []
            for r in s.in_ids("phx_dm_region_in_division", scope_id):
                ids.extend(s.in_ids("phx_dm_market_in_region", r))
            return ids
        if st == "REGION":
            return list(s.in_ids("phx_dm_market_in_region", scope_id))
        return []

    def _market_row(self, market_id: str) -> dict:
        advisors = self._store.in_ids("phx_dm_advisor_in_market", market_id)
        rev = sum(self._rev_ltm(a) for a in advisors)
        return {
            "scope_type": "Market",
            "scope_id": market_id,
            "label": self._name("phx_dm_market", market_id, "market_name"),
            "revenue_ltm": round(rev, 2),
            "advisor_count": len(advisors),
            "rev_per_advisor": round(rev / len(advisors), 2) if advisors else 0.0,
        }

    def _markets(self, scope_type: str, scope_id: str, limit: int = 5) -> dict:
        """Top & bottom markets under the scope, ranked by aggregate LTM revenue."""
        market_ids = self._markets_under(scope_type, scope_id)
        rows = [self._market_row(m) for m in market_ids]
        rows = [r for r in rows if r["advisor_count"] > 0]
        rows.sort(key=lambda r: r["revenue_ltm"], reverse=True)
        return {"top": rows[:limit], "bottom": rows[-limit:][::-1] if len(rows) > limit else []}

    def _peer_scope_ids(self, scope_type: str, scope_id: str) -> tuple[str, list[str]]:
        """The peer group for 'Benchmarking (vs Peers)': same-type siblings under the
        same parent. Firm has no same-type peer, so it benchmarks its divisions."""
        s = self._store
        st = scope_type.upper()
        if st == "FIRM":
            return "Division", list(s.in_ids("phx_dm_division_in_firm", scope_id))
        if st == "DIVISION":
            return "Division", list(s.in_ids("phx_dm_division_in_firm", self._firm_id()))
        if st == "REGION":
            divs = list(s.out_ids("phx_dm_region_in_division", scope_id))
            div = divs[0] if divs else None
            return "Region", (list(s.in_ids("phx_dm_region_in_division", div)) if div else [])
        if st == "MARKET":
            regs = list(s.out_ids("phx_dm_market_in_region", scope_id))
            reg = regs[0] if regs else None
            return "Market", (list(s.in_ids("phx_dm_market_in_region", reg)) if reg else [])
        return "Advisor", []

    def _per_advisor_rev(self, scope_type: str, scope_id: str) -> tuple[float, int]:
        advisors = resolve_scope_advisor_ids(self._store, scope_type.upper(), scope_id)
        rev = sum(self._rev_ltm(a) for a in advisors)
        return (round(rev / len(advisors), 2) if advisors else 0.0), len(advisors)

    def _name_for_scope(self, scope_type: str, scope_id: str) -> str:
        attr = {
            "FIRM": ("phx_dm_firm", "firm_name"),
            "DIVISION": ("phx_dm_division", "division_name"),
            "REGION": ("phx_dm_region", "region_name"),
            "MARKET": ("phx_dm_market", "market_name"),
            "ADVISOR": ("phx_dm_advisor", "advisor_name"),
        }.get(scope_type.upper())
        return self._name(attr[0], scope_id, attr[1]) if attr else scope_id

    def _benchmark(self, scope_type: str, scope_id: str) -> dict:
        """Revenue-per-advisor of the current scope vs its peer scopes + the firm
        average, with the current scope's percentile. Real values from snapshots."""
        peer_type, peer_ids = self._peer_scope_ids(scope_type, scope_id)
        firm_per, _ = self._per_advisor_rev("FIRM", self._firm_id())
        rows = []
        for pid in peer_ids:
            per, cnt = self._per_advisor_rev(peer_type, pid)
            if cnt == 0:
                continue
            rows.append({
                "scope_id": pid,
                "label": self._name_for_scope(peer_type, pid),
                "per_advisor": per,
                "advisor_count": cnt,
                "is_current": pid == scope_id,
            })
        rows.sort(key=lambda r: r["per_advisor"], reverse=True)
        this_per, this_cnt = self._per_advisor_rev(scope_type, scope_id)
        # percentile of the current scope among its peers
        percentile = None
        if peer_ids and scope_type.upper() != "FIRM":
            vals = sorted(r["per_advisor"] for r in rows)
            below = sum(1 for v in vals if v < this_per)
            percentile = round(below / len(vals) * 100) if vals else None
        return {
            "peer_type": peer_type,
            "current_per_advisor": this_per,
            "current_advisor_count": this_cnt,
            "firm_per_advisor": firm_per,
            "vs_firm_pct": round((this_per - firm_per) / firm_per * 100, 1) if firm_per else None,
            "percentile": percentile,
            "rows": rows,
        }

    def _headline(self, scope_type: str, scope_id: str, compare_to: str, revenue: dict, benchmark: dict) -> dict:
        """The period revenue figure + the delta the Compare-To control asks for."""
        total = float(revenue.get("kpis", {}).get("total_revenue") or 0.0)
        ct = (compare_to or "Prior Year").strip()
        if ct == "None":
            return {"revenue": round(total, 2), "delta_pct": None, "basis": "no comparison", "compare_to": ct}
        if ct == "Prior Period":
            c = revenue.get("comparison_prior_period", {})
            return {"revenue": round(total, 2), "delta_pct": c.get("change_pct"),
                    "prior": c.get("prior_revenue"), "basis": c.get("basis"), "compare_to": ct}
        if ct == "Peer Benchmark":
            return {"revenue": round(total, 2), "delta_pct": benchmark.get("vs_firm_pct"),
                    "prior": None, "basis": "revenue-per-advisor vs firm average", "compare_to": ct}
        c = revenue.get("comparison", {})  # Prior Year (default)
        return {"revenue": round(total, 2), "delta_pct": c.get("change_pct"),
                "prior": c.get("prior_revenue"), "basis": c.get("basis"), "compare_to": "Prior Year"}

    # ---- main --------------------------------------------------------------
    def dashboard(self, scope_type: str = "FIRM", scope_id: str = "F001",
                  period: str = "LTM", compare_to: str = "Prior Year") -> dict:
        st = (scope_type or "FIRM").upper()
        rollup = ScopeRollupService().summary(scope_type=st, scope_id=scope_id)
        revenue = RevenueAnalyticsService().analytics(st, scope_id, period=period)
        markets = self._markets(st, scope_id)
        benchmark = self._benchmark(st, scope_id)
        headline = self._headline(st, scope_id, compare_to, revenue, benchmark)
        return {
            "scope_type": st,
            "scope_id": scope_id,
            "period": (period or "LTM").upper(),
            "compare_to": compare_to,
            "headline": headline,
            "totals": rollup["totals"],
            "comparison": rollup["comparison"],
            "top_advisors": rollup["top_advisors"],
            "bottom_advisors": rollup["bottom_advisors"],
            "child_breakdown": rollup["child_breakdown"],
            "revenue": {
                "monthly_trend": revenue.get("monthly_trend", []),
                "by_business_line": revenue.get("by_business_line", []),
                "by_channel": revenue.get("by_channel", []),
                "revenue_drivers": revenue.get("revenue_drivers", []),
                "by_geography": revenue.get("by_geography", []),
                "kpis": revenue.get("kpis", {}),
                "comparison": revenue.get("comparison", {}),
            },
            "markets": markets,
            "benchmark": benchmark,
            "evidence": rollup["evidence"],
        }
