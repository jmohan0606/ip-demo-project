from __future__ import annotations

from collections import defaultdict

from app.graph.client import get_graph_client
from app.graph.queries.common import advisor_transactions, resolve_scope_advisor_ids

# one drill-down level: child scope type + parent->child edge + child vertex +
# its name attr (same hierarchy the scope rollup uses).
_CHILDREN = {
    "FIRM": ("Division", "phx_dm_division_in_firm", "phx_dm_division", "division_name"),
    "DIVISION": ("Region", "phx_dm_region_in_division", "phx_dm_region", "region_name"),
    "REGION": ("Market", "phx_dm_market_in_region", "phx_dm_market", "market_name"),
    "MARKET": ("Advisor", "phx_dm_advisor_in_market", "phx_dm_advisor", "advisor_name"),
}


class RevenueAnalyticsService:
    """Revenue intelligence for a hierarchy scope, computed from the REAL revenue
    transactions in the graph (phx_dm_revenue_transaction -> advisor). Monthly
    trend, channel mix, and per-child breakdown are all Σ revenue_amount over the
    scope's resolved advisors — no synthetic series."""

    def __init__(self) -> None:
        self._store = get_graph_client().store

    def _name(self, vtype: str, vid: str, attr: str) -> str:
        return str((self._store.vertex(vtype, vid) or {}).get(attr) or vid)

    @staticmethod
    def _rev(attrs: dict) -> float:
        return float(attrs.get("revenue_amount") or 0.0)

    def analytics(self, scope_type: str = "FIRM", scope_id: str = "F001") -> dict:
        st = (scope_type or "FIRM").upper()
        advisor_ids = resolve_scope_advisor_ids(self._store, st, scope_id)
        rows = [attrs for _, attrs in advisor_transactions(self._store, advisor_ids)]

        by_month: dict[str, float] = defaultdict(float)
        by_type: dict[str, float] = defaultdict(float)
        total = 0.0
        for a in rows:
            rev = self._rev(a)
            total += rev
            by_month[str(a.get("transaction_date"))[:7]] += rev
            by_type[str(a.get("transaction_type") or "OTHER")] += rev

        monthly_trend = [
            {"month": m, "revenue": round(v, 2)} for m, v in sorted(by_month.items()) if m and m != "None"
        ]
        by_channel = sorted(
            ({"channel": t, "revenue": round(v, 2)} for t, v in by_type.items()),
            key=lambda r: r["revenue"],
            reverse=True,
        )

        # per-child revenue (transactions summed under each immediate child scope)
        by_child = []
        if st != "ADVISOR" and st in _CHILDREN:
            child_type, edge, child_vtype, name_attr = _CHILDREN[st]
            for child_id in sorted(self._store.in_ids(edge, scope_id)):
                child_ids = resolve_scope_advisor_ids(self._store, child_type, child_id)
                child_rev = sum(self._rev(attrs) for _, attrs in advisor_transactions(self._store, child_ids))
                by_child.append({
                    "scope_type": child_type,
                    "scope_id": child_id,
                    "label": self._name(child_vtype, child_id, name_attr),
                    "revenue": round(child_rev, 2),
                    "advisor_count": len(child_ids),
                })
            by_child.sort(key=lambda r: r["revenue"], reverse=True)

        top_channel = by_channel[0]["channel"] if by_channel else None
        return {
            "scope_type": st,
            "scope_id": scope_id,
            "kpis": {
                "total_revenue": round(total, 2),
                "transaction_count": len(rows),
                "advisor_count": len(advisor_ids),
                "avg_revenue_per_advisor": round(total / len(advisor_ids), 2) if advisor_ids else 0.0,
                "months_covered": len(monthly_trend),
                "top_channel": top_channel,
            },
            "monthly_trend": monthly_trend,
            "by_channel": by_channel,
            "by_child": by_child,
            "evidence": {
                "source": "phx_dm_revenue_transaction vertices via transaction_for_advisor edges",
                "advisor_ids_resolved": len(advisor_ids),
                "computation": "Σ revenue_amount grouped by transaction month / transaction_type / child scope",
            },
        }
