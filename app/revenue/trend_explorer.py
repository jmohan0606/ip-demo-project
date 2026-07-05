from __future__ import annotations

from collections import defaultdict

from app.graph.client import get_graph_client
from app.graph.queries.common import advisor_transactions, resolve_scope_advisor_ids
from app.llm.client import get_llm_client

# dimension -> how an advisor (or transaction) maps to a slice of that dimension.
# Hierarchy dimensions resolve advisor -> member via the same edges the scope
# rollup uses; business_line resolves per-transaction via product -> category.
_DIM_VERTEX = {
    "division": ("phx_dm_division", "division_name"),
    "region": ("phx_dm_region", "region_name"),
    "market": ("phx_dm_market", "market_name"),
    "branch": ("phx_dm_branch", "branch_name"),
    "advisor": ("phx_dm_advisor", "advisor_name"),
}

_MAX_SLICES = 5  # top-N slices charted individually; remainder folds into "Other"
_OTHER = "Other"


def _q_label(ym: str) -> str:
    return f"{ym[:4]}-Q{(int(ym[5:7]) - 1) // 3 + 1}"


def _prior_period(period: str, granularity: str) -> str:
    """The immediately preceding comparable bucket (prior month / prior quarter)."""
    if granularity == "quarterly":
        y, q = int(period[:4]), int(period[6])
        return f"{y - 1}-Q4" if q == 1 else f"{y}-Q{q - 1}"
    y, m = int(period[:4]), int(period[5:7])
    idx = y * 12 + (m - 1) - 1
    return f"{idx // 12:04d}-{idx % 12 + 1:02d}"


class RevenueTrendExplorerService:
    """Revenue Trend Explorer (CLAUDE.md 9.6): revenue per period bucket, sliced by a
    user-selected dimension, with a per-period AI driver summary grounded in the real
    figures. Every number is Σ revenue_amount over real phx_dm_revenue_transaction
    vertices — the per-advisor monthly sums are computed once, then rolled up per
    dimension/granularity, so the endpoint stays fast at 36 periods × N slices.
    """

    def __init__(self) -> None:
        self._store = get_graph_client().store

    # ---- slice resolution ----------------------------------------------------
    def _advisor_slice_map(self, advisor_ids: list[str], dimension: str) -> dict[str, str]:
        """advisor_id -> slice label for hierarchy dimensions (division/region/
        market/branch/advisor), resolved once via the real hierarchy edges."""
        s = self._store
        vtype, name_attr = _DIM_VERTEX[dimension]

        def name(vid: str) -> str:
            return str((s.vertex(vtype, vid) or {}).get(name_attr) or vid)

        out: dict[str, str] = {}
        for aid in advisor_ids:
            member: str | None = None
            if dimension == "advisor":
                member = aid
            elif dimension == "branch":
                member = next(iter(s.out_ids("phx_dm_advisor_in_branch", aid)), None)
            else:
                market = next(iter(s.out_ids("phx_dm_advisor_in_market", aid)), None)
                if dimension == "market":
                    member = market
                elif market is not None:
                    region = next(iter(s.out_ids("phx_dm_market_in_region", market)), None)
                    if dimension == "region":
                        member = region
                    elif region is not None:  # division
                        member = next(iter(s.out_ids("phx_dm_region_in_division", region)), None)
            out[aid] = name(member) if member else "Unassigned"
        return out

    def _product_category_map(self) -> dict[str, str]:
        """product_id -> business-line category_name via product_in_subcategory ->
        subcategory_in_category (same chain RevenueAnalyticsService uses)."""
        s = self._store
        cats = s.all_vertices("phx_dm_product_category")
        out: dict[str, str] = {}
        for pid in s.all_vertices("phx_dm_product"):
            name = "Unclassified"
            subs = s.out_ids("phx_dm_product_in_subcategory", pid)
            if subs:
                cat_ids = s.out_ids("phx_dm_subcategory_in_category", subs[0])
                if cat_ids:
                    name = str((cats.get(cat_ids[0]) or {}).get("category_name") or cat_ids[0])
            out[pid] = name
        return out

    # ---- AI driver summary -----------------------------------------------------
    @staticmethod
    def _driver_summary(llm, period: str, total: float, change_pct: float | None,
                        slices: dict[str, float], movers: dict[str, float], dimension: str) -> str:
        """2-3 sentence driver summary grounded ONLY in this period's real figures."""
        ranked = sorted(slices.items(), key=lambda kv: kv[1], reverse=True)
        top_label, top_rev = ranked[0] if ranked else ("n/a", 0.0)
        biggest_mover = max(movers.items(), key=lambda kv: abs(kv[1]), default=(None, 0.0))
        context = {
            "period": period,
            "total_revenue": f"${total:,.0f}",
            "change_vs_prior_period": f"{change_pct:+.1f}%" if change_pct is not None else "no prior period in data",
            "dimension": dimension,
            f"top_{dimension}": f"{top_label} (${top_rev:,.0f}, {top_rev / total * 100:.0f}% of period)" if total else top_label,
            "biggest_mover_vs_prior": (
                f"{biggest_mover[0]} ({biggest_mover[1]:+,.0f} vs prior period)" if biggest_mover[0] else None
            ),
        }
        prompt = (
            f"In 2-3 sentences, summarize the revenue drivers for period {period}. "
            f"State the total, the direction vs the prior period, the leading {dimension}, "
            "and the biggest mover. Use ONLY the figures in the context — do not invent numbers."
        )
        return llm.generate(prompt, context)

    # ---- main --------------------------------------------------------------------
    def trend(
        self,
        dimension: str = "division",
        granularity: str = "monthly",
        start: str | None = None,
        end: str | None = None,
        scope_type: str = "FIRM",
        scope_id: str = "F001",
    ) -> dict:
        dimension = (dimension or "division").lower()
        if dimension not in (*_DIM_VERTEX, "business_line"):
            raise ValueError(f"Unknown dimension '{dimension}'")
        granularity = "quarterly" if (granularity or "").lower() == "quarterly" else "monthly"

        advisor_ids = resolve_scope_advisor_ids(self._store, (scope_type or "FIRM").upper(), scope_id)

        # -- single pass over real transactions: (month, slice) -> Σ revenue_amount
        by_line = dimension == "business_line"
        adv_slice = {} if by_line else self._advisor_slice_map(advisor_ids, dimension)
        cat_by_product = self._product_category_map() if by_line else {}
        month_slice: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        tx_count = 0
        for aid in advisor_ids:
            for tx_id, attrs in advisor_transactions(self._store, [aid]):
                month = str(attrs.get("transaction_date"))[:7]
                if not month or month == "None":
                    continue
                rev = float(attrs.get("revenue_amount") or 0.0)
                if by_line:
                    pids = self._store.out_ids("phx_dm_transaction_for_product", tx_id)
                    label = cat_by_product.get(pids[0], "Unclassified") if pids else "Unclassified"
                else:
                    label = adv_slice.get(aid, "Unassigned")
                month_slice[month][label] += rev
                tx_count += 1

        available_months = sorted(month_slice)
        if not available_months:
            return {
                "scope_type": scope_type, "scope_id": scope_id, "dimension": dimension,
                "granularity": granularity, "start": start, "end": end,
                "available_months": [], "slices": [], "periods": [],
                "evidence": {"source": "phx_dm_revenue_transaction", "transaction_count": 0},
            }
        start = start or available_months[0]
        end = end or available_months[-1]

        # -- roll monthly sums up to the requested granularity (ALL periods, so the
        #    first in-range period still has a real prior bucket to compare against)
        bucket_slice: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for month, sl in month_slice.items():
            bucket = _q_label(month) if granularity == "quarterly" else month
            for label, rev in sl.items():
                bucket_slice[bucket][label] += rev
        bucket_total = {b: sum(sl.values()) for b, sl in bucket_slice.items()}

        def in_range(bucket: str) -> bool:
            if granularity == "quarterly":
                return _q_label(start) <= bucket <= _q_label(end)
            return start <= bucket <= end

        range_buckets = sorted(b for b in bucket_slice if in_range(b))

        # -- fixed top-N slice identity over the whole requested range (stable colors)
        slice_totals: dict[str, float] = defaultdict(float)
        for b in range_buckets:
            for label, rev in bucket_slice[b].items():
                slice_totals[label] += rev
        top_slices = [l for l, _ in sorted(slice_totals.items(), key=lambda kv: kv[1], reverse=True)[:_MAX_SLICES]]
        has_other = len(slice_totals) > len(top_slices)

        def fold(sl: dict[str, float]) -> dict[str, float]:
            out = {label: round(sl.get(label, 0.0), 2) for label in top_slices}
            other = sum(v for l, v in sl.items() if l not in top_slices)
            if has_other:
                out[_OTHER] = round(other, 2)
            return out

        llm = get_llm_client()
        periods = []
        for b in range_buckets:
            total = bucket_total[b]
            prior_b = _prior_period(b, granularity)
            prior_total = bucket_total.get(prior_b)
            change_pct = (
                round((total - prior_total) / prior_total * 100, 1)
                if prior_total else None
            )
            folded = fold(bucket_slice[b])
            prior_folded = fold(bucket_slice.get(prior_b, {})) if prior_total is not None else {}
            movers = {l: folded[l] - prior_folded.get(l, 0.0) for l in folded} if prior_folded else {}
            periods.append({
                "period": b,
                "total_revenue": round(total, 2),
                "prior_period": prior_b if prior_total is not None else None,
                "prior_revenue": round(prior_total, 2) if prior_total is not None else None,
                "change_pct": change_pct,
                "slices": folded,
                "top_slice": max(folded, key=folded.get) if folded else None,
                "driver_summary": self._driver_summary(llm, b, total, change_pct, folded, movers, dimension),
            })

        return {
            "scope_type": (scope_type or "FIRM").upper(),
            "scope_id": scope_id,
            "dimension": dimension,
            "granularity": granularity,
            "start": start,
            "end": end,
            "available_months": available_months,
            "slices": top_slices + ([_OTHER] if has_other else []),
            "periods": periods,
            "evidence": {
                "source": "phx_dm_revenue_transaction via phx_dm_transaction_for_advisor",
                "advisor_ids_resolved": len(advisor_ids),
                "transaction_count": tx_count,
                "computation": (
                    f"Σ revenue_amount grouped by {granularity} period × {dimension} "
                    f"(top {_MAX_SLICES} slices by range total, remainder folded into '{_OTHER}'); "
                    "change_pct = vs immediately preceding period bucket; driver summaries are "
                    "LLM-generated from ONLY these computed figures"
                ),
                "llm": llm.describe(),
            },
        }
