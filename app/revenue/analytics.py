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


def _shift_month(ym: str, delta_months: int) -> str:
    """Shift a 'YYYY-MM' string by delta_months (can be negative)."""
    y, m = int(ym[:4]), int(ym[5:7])
    idx = (y * 12 + (m - 1)) + delta_months
    return f"{idx // 12:04d}-{idx % 12 + 1:02d}"


class RevenueAnalyticsService:
    """Revenue intelligence for a hierarchy scope, computed from the REAL revenue
    transactions in the graph (phx_dm_revenue_transaction -> advisor). Trend,
    channel mix, business-line mix, geographic (by-state) distribution and the
    per-child scope breakdown are all Σ revenue_amount over the scope's resolved
    advisors — no synthetic series. Every dimension links back to real edges:
      channel        = revenue_transaction.transaction_type
      business line  = transaction_for_product -> product_in_subcategory -> subcategory_in_category
      geography      = advisor_in_branch -> branch.state
      scope children = the same hierarchy edges the scope rollup uses
    """

    def __init__(self) -> None:
        self._store = get_graph_client().store
        self._cat_by_product = self._build_product_category_map()

    # ---- lookups -----------------------------------------------------------
    def _name(self, vtype: str, vid: str, attr: str) -> str:
        return str((self._store.vertex(vtype, vid) or {}).get(attr) or vid)

    @staticmethod
    def _rev(attrs: dict) -> float:
        return float(attrs.get("revenue_amount") or 0.0)

    def _build_product_category_map(self) -> dict[str, str]:
        """product_id -> business-line category_name, resolved once via
        product_in_subcategory -> subcategory_in_category (64 products)."""
        s = self._store
        cats = s.all_vertices("phx_dm_product_category")
        out: dict[str, str] = {}
        for pid in s.all_vertices("phx_dm_product"):
            name = "Unclassified"
            for sub in s.out_ids("phx_dm_product_in_subcategory", pid):
                for cat in s.out_ids("phx_dm_subcategory_in_category", sub):
                    name = str((cats.get(cat) or {}).get("category_name") or cat)
                    break
                break
            out[pid] = name
        return out

    def _tx_category(self, tx_id: str) -> str:
        for pid in self._store.out_ids("phx_dm_transaction_for_product", tx_id):
            return self._cat_by_product.get(pid, "Unclassified")
        return "Unclassified"

    # ---- period filtering --------------------------------------------------
    @staticmethod
    def _current_months(all_months: list[str], period: str) -> set[str]:
        """The set of 'YYYY-MM' months included by the Time Period dropdown,
        anchored to the most recent transaction month. LTM = trailing 12."""
        months = sorted({m for m in all_months if m and m != "None"})
        if not months:
            return set()
        ref = months[-1]
        ry, rm = int(ref[:4]), int(ref[5:7])
        p = (period or "ALL").upper()
        if p in ("ALL", "ALLTIME", ""):
            return set(months)
        if p == "MTD":
            return {ref}
        if p == "QTD":
            q = (rm - 1) // 3
            return {m for m in months if int(m[:4]) == ry and ((int(m[5:7]) - 1) // 3) == q}
        if p == "YTD":
            return {m for m in months if int(m[:4]) == ry}
        # LTM: trailing 12 calendar months present in data
        return set(months[-12:])

    # ---- main --------------------------------------------------------------
    def analytics(self, scope_type: str = "FIRM", scope_id: str = "F001", period: str = "ALL") -> dict:
        st = (scope_type or "FIRM").upper()
        advisor_ids = resolve_scope_advisor_ids(self._store, st, scope_id)

        # single traversal per advisor -> keeps advisor identity for the geo map
        adv_rows: dict[str, list[tuple[str, dict]]] = {
            aid: advisor_transactions(self._store, [aid]) for aid in advisor_ids
        }
        all_rows = [(tx, a) for rows in adv_rows.values() for tx, a in rows]
        all_months = [str(a.get("transaction_date"))[:7] for _, a in all_rows]

        cur_months = self._current_months(all_months, period)
        prior_months = {_shift_month(m, -12) for m in cur_months}
        # YoY is only honest when every current month has a real prior-year month in the
        # data. ALL (36mo) shifts partly off the start of the series, so its delta is
        # suppressed; MTD/QTD/YTD/LTM stay fully covered.
        data_months = {m for m in all_months if m and m != "None"}
        prior_fully_covered = bool(cur_months) and prior_months.issubset(data_months)

        def in_cur(a: dict) -> bool:
            return str(a.get("transaction_date"))[:7] in cur_months

        by_month: dict[str, float] = defaultdict(float)
        by_type: dict[str, float] = defaultdict(float)
        by_line: dict[str, float] = defaultdict(float)
        total = 0.0
        kept_count = 0
        prior_total = 0.0
        for tx, a in all_rows:
            month = str(a.get("transaction_date"))[:7]
            rev = self._rev(a)
            if month in prior_months:
                prior_total += rev
            if month not in cur_months:
                continue
            kept_count += 1
            total += rev
            by_month[month] += rev
            by_type[str(a.get("transaction_type") or "OTHER")] += rev
            by_line[self._tx_category(tx)] += rev

        monthly_trend = [{"month": m, "revenue": round(v, 2)} for m, v in sorted(by_month.items())]
        by_channel = sorted(
            ({"channel": t, "revenue": round(v, 2)} for t, v in by_type.items()),
            key=lambda r: r["revenue"], reverse=True,
        )
        by_business_line = sorted(
            ({"category": c, "revenue": round(v, 2)} for c, v in by_line.items()),
            key=lambda r: r["revenue"], reverse=True,
        )

        # geographic distribution: advisor -> branch.state
        state_rev: dict[str, float] = defaultdict(float)
        state_adv: dict[str, set[str]] = defaultdict(set)
        for aid, rows in adv_rows.items():
            branch_ids = self._store.out_ids("phx_dm_advisor_in_branch", aid)
            state = None
            for bid in branch_ids:
                state = (self._store.vertex("phx_dm_branch", bid) or {}).get("state")
                if state:
                    break
            if not state:
                continue
            adv_rev = sum(self._rev(a) for _, a in rows if in_cur(a))
            if adv_rev:
                state_rev[state] += adv_rev
                state_adv[state].add(aid)
        by_geography = sorted(
            (
                {"state": st_, "revenue": round(v, 2), "advisor_count": len(state_adv[st_])}
                for st_, v in state_rev.items()
            ),
            key=lambda r: r["revenue"], reverse=True,
        )

        # per-child revenue (transactions summed under each immediate child scope)
        by_child = []
        if st != "ADVISOR" and st in _CHILDREN:
            child_type, edge, child_vtype, name_attr = _CHILDREN[st]
            for child_id in sorted(self._store.in_ids(edge, scope_id)):
                child_ids = resolve_scope_advisor_ids(self._store, child_type, child_id)
                child_rev = sum(
                    self._rev(attrs)
                    for _, attrs in advisor_transactions(self._store, child_ids)
                    if in_cur(attrs)
                )
                by_child.append({
                    "scope_type": child_type,
                    "scope_id": child_id,
                    "label": self._name(child_vtype, child_id, name_attr),
                    "revenue": round(child_rev, 2),
                    "advisor_count": len(child_ids),
                })
            by_child.sort(key=lambda r: r["revenue"], reverse=True)

        top_channel = by_channel[0]["channel"] if by_channel else None
        top_line = by_business_line[0]["category"] if by_business_line else None
        change_pct = (
            round((total - prior_total) / prior_total * 100, 1)
            if (prior_fully_covered and prior_total > 0)
            else None
        )
        return {
            "scope_type": st,
            "scope_id": scope_id,
            "kpis": {
                "total_revenue": round(total, 2),
                "transaction_count": kept_count,
                "advisor_count": len(advisor_ids),
                "avg_revenue_per_advisor": round(total / len(advisor_ids), 2) if advisor_ids else 0.0,
                "months_covered": len(monthly_trend),
                "top_channel": top_channel,
                "top_business_line": top_line,
                "period": (period or "ALL").upper(),
            },
            "comparison": {
                "prior_revenue": round(prior_total, 2) if prior_fully_covered else None,
                "change_pct": change_pct,
                "basis": "same period, prior year (months shifted -12)",
            },
            "monthly_trend": monthly_trend,
            "by_channel": by_channel,
            "by_business_line": by_business_line,
            "by_geography": by_geography,
            "by_child": by_child,
            "evidence": {
                "source": "phx_dm_revenue_transaction vertices via transaction_for_advisor edges",
                "advisor_ids_resolved": len(advisor_ids),
                "computation": (
                    "Σ revenue_amount grouped by month / transaction_type (channel) / "
                    "product→subcategory→category (business line) / advisor→branch.state (geography) / child scope"
                ),
            },
        }
