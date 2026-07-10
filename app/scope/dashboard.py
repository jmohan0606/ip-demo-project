from __future__ import annotations

import logging

from app.graph.client import get_graph_client
from app.graph.queries.common import (
    resolve_scope_advisor_ids_graph,
    run_catalog_query,
    scope_advisor_placements,
)
from app.features.snapshot_store import SnapshotStore
from app.scope.rollup import ScopeRollupService
from app.revenue.analytics import RevenueAnalyticsService

logger = logging.getLogger(__name__)

# Wide DATETIME bounds for GQ-051 (required params; cover the full data range).
_DATE_MIN = "1900-01-01 00:00:00"
_DATE_MAX = "2100-01-01 00:00:00"


class ScopeDashboardService:
    """Composes everything the Executive Dashboard (12.1) needs into ONE
    period-aware, scope-aware payload: the rollup totals + status + top/bottom
    advisors (snapshot-based), the period-windowed revenue trend / product-category
    / channel / geography / YoY drivers (RevenueAnalyticsService), top & bottom
    markets, a peer benchmark, and a headline revenue figure whose delta respects
    the Compare-To control (Prior Year | Prior Period | Peer Benchmark | None).
    Every number is a real sum/mean over resolved advisors — no hardcoded totals."""

    def __init__(self) -> None:
        self._graph = get_graph_client()
        self._store = self._graph.store  # logged fallback path only — reads go via run_query
        self._snaps = SnapshotStore()
        self._pl_cache: dict[tuple[str, str], dict[str, dict] | None] = {}
        self._scope_labels: dict[tuple[str, str], str] = {}

    def _pl(self, scope_type: str, scope_id: str) -> dict[str, dict] | None:
        """Cached GQ-053 placements per (scope_type, scope_id); also feeds the
        scope-label cache used by _name_for_scope."""
        key = (scope_type.upper(), str(scope_id))
        if key not in self._pl_cache:
            placements = scope_advisor_placements(self._graph, key[0], key[1])
            if placements:
                for aid, p in placements.items():
                    self._scope_labels[("ADVISOR", aid)] = str(p.get("advisor_name") or aid)
                    for level in ("market", "region", "division", "firm"):
                        lid = str(p.get(f"{level}_id") or "")
                        if lid:
                            self._scope_labels[(level.upper(), lid)] = str(p.get(f"{level}_name") or lid)
            self._pl_cache[key] = placements
        return self._pl_cache[key]

    # ---- helpers -----------------------------------------------------------
    def _rev_ltm(self, advisor_id: str) -> float:
        snap = self._snaps.latest_for_entity("ADVISOR", advisor_id)
        f = (snap or {}).get("features", {}) if snap else {}
        v = f.get("revenue_ltm")
        return float(v) if v is not None else 0.0

    def _name(self, vtype: str, vid: str, attr: str) -> str:
        return str((self._store.vertex(vtype, vid) or {}).get(attr) or vid)

    def _firm_id(self) -> str:
        for key, _ in self._scope_labels.items():
            if key[0] == "FIRM":
                return key[1]
        for placements in self._pl_cache.values():
            for p in (placements or {}).values():
                if p.get("firm_id"):
                    return str(p["firm_id"])
        firms = list(self._store.all_vertices("phx_dm_firm").keys())  # logged-fallback store
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
        """Top & bottom markets under the scope, ranked by aggregate LTM revenue.
        Markets and their advisors come from the GQ-053 placements of the scope;
        direct store traversal only on the logged fallback path."""
        if scope_type.upper() not in ("FIRM", "DIVISION", "REGION"):
            return {"top": [], "bottom": []}  # no markets *under* market/advisor scope
        placements = self._pl(scope_type, scope_id)
        if placements is not None:
            groups: dict[str, dict] = {}
            for aid, p in placements.items():
                mid = str(p.get("market_id") or "")
                if not mid:
                    continue
                g = groups.setdefault(mid, {"label": str(p.get("market_name") or mid), "advisors": []})
                g["advisors"].append(aid)
            rows = []
            for mid, g in groups.items():
                rev = sum(self._rev_ltm(a) for a in g["advisors"])
                rows.append({
                    "scope_type": "Market",
                    "scope_id": mid,
                    "label": g["label"],
                    "revenue_ltm": round(rev, 2),
                    "advisor_count": len(g["advisors"]),
                    "rev_per_advisor": round(rev / len(g["advisors"]), 2) if g["advisors"] else 0.0,
                })
            # placements only include markets that have advisors, matching the
            # advisor_count > 0 filter of the traversal path below
        else:
            logger.warning("markets ranking for %s/%s using local store traversal fallback",
                           scope_type, scope_id)
            market_ids = self._markets_under(scope_type, scope_id)
            rows = [self._market_row(m) for m in market_ids]
            rows = [r for r in rows if r["advisor_count"] > 0]
        rows.sort(key=lambda r: r["revenue_ltm"], reverse=True)
        return {"top": rows[:limit], "bottom": rows[-limit:][::-1] if len(rows) > limit else []}

    def _peer_scope_ids(self, scope_type: str, scope_id: str) -> tuple[str, list[str]]:
        """The peer group for 'Benchmarking (vs Peers)': same-type siblings under the
        same parent, resolved from GQ-053 placements (current scope's rows locate the
        parent; the parent scope's rows enumerate the siblings). Direct store
        traversal only on the logged fallback path."""
        st = scope_type.upper()
        my = self._pl(st, scope_id)
        if my is not None:
            def ids_under(parent_type: str, parent_id: str, level: str) -> list[str]:
                placements = self._pl(parent_type, parent_id) or {}
                return sorted({str(p.get(f"{level}_id")) for p in placements.values() if p.get(f"{level}_id")})

            first = next(iter(my.values()), {})
            if st == "FIRM":
                return "Division", ids_under("FIRM", scope_id, "division")
            if st == "DIVISION":
                firm = str(first.get("firm_id") or "") or self._firm_id()
                return "Division", ids_under("FIRM", firm, "division")
            if st == "REGION":
                div = str(first.get("division_id") or "")
                return "Region", (ids_under("DIVISION", div, "region") if div else [])
            if st == "MARKET":
                reg = str(first.get("region_id") or "")
                return "Market", (ids_under("REGION", reg, "market") if reg else [])
            return "Advisor", []
        logger.warning("peer-scope resolution for %s/%s using local store traversal fallback",
                       st, scope_id)
        s = self._store
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
        advisors = resolve_scope_advisor_ids_graph(self._graph, scope_type.upper(), scope_id)
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
        label = self._scope_labels.get((scope_type.upper(), str(scope_id)))
        if label:
            return label
        return self._name(attr[0], scope_id, attr[1]) if attr else scope_id

    # ---- advisor-scope GNN peer benchmark (REQ-2: the similarity engine IS the
    # peer group — never "no peer group at this scope") --------------------------
    def _gnn_peers(self, advisor_id: str, top_k: int = 5) -> tuple[str, list[dict]]:
        """Nearest advisors by GNN (GraphSAGE) embedding cosine, via the same
        VectorClient the /graph-insights/similar endpoint serves. Falls back to the
        deterministic feature-projection similarity engine if no vector exists."""
        try:
            from app.ml import registry
            from app.ml.vector_client import get_vector_client
            vc = get_vector_client()
            model = registry.active_embedding_model()
            vec = vc.get("ADVISOR", advisor_id, model_name=model)
            if vec is not None:
                matches = vc.search("ADVISOR", vec, top_k, exclude_id=advisor_id, model_name=model)
                return model, [{"advisor_id": m["entity_id"], "score": round(float(m["score"]), 4)} for m in matches]
        except Exception:
            pass
        try:  # fallback: deterministic feature-projection similarity (still the real engine)
            from app.services.embedding_similarity_service import EmbeddingSimilarityService
            res = EmbeddingSimilarityService().similar(advisor_id, limit=top_k)
            return "deterministic-feature-projection", [
                {"advisor_id": m["target_entity_id"], "score": round(float(m["similarity_score"]), 4)}
                for m in res.get("matches", [])
            ]
        except Exception:
            return "unavailable", []

    def _advisor_benchmark(self, advisor_id: str) -> dict:
        """Benchmarking (vs Peers) at ADVISOR scope: the peer group is the GNN
        similarity engine's real nearest advisors; every metric compares the
        advisor's snapshot against the peer-group mean. You / Peer Avg / vs Peer,
        exactly the mockup's table."""
        model, peers = self._gnn_peers(advisor_id)
        me = (self._snaps.latest_for_entity("ADVISOR", advisor_id) or {}).get("features", {})

        feats_by_peer: dict[str, dict] = {}
        for p in peers:
            f = (self._snaps.latest_for_entity("ADVISOR", p["advisor_id"]) or {}).get("features", {})
            peer_pl = (self._pl("ADVISOR", p["advisor_id"]) or {}).get(p["advisor_id"])
            if peer_pl is not None:
                p["advisor_name"] = str(peer_pl.get("advisor_name") or p["advisor_id"])
                p["market"] = str(peer_pl.get("market_name")) if peer_pl.get("market_name") else None
            else:  # logged-fallback store path
                p["advisor_name"] = self._name("phx_dm_advisor", p["advisor_id"], "advisor_name")
                markets = self._store.out_ids("phx_dm_advisor_in_market", p["advisor_id"])
                p["market"] = self._name("phx_dm_market", markets[0], "market_name") if markets else None
            if f:
                feats_by_peer[p["advisor_id"]] = f
        peer_feats = list(feats_by_peer.values())

        def avg(key: str, scale: float = 1.0) -> float | None:
            vals = [float(f[key]) * scale for f in peer_feats if f.get(key) is not None]
            return round(sum(vals) / len(vals), 2) if vals else None

        def mine(key: str, scale: float = 1.0) -> float | None:
            v = me.get(key)
            return round(float(v) * scale, 2) if v is not None else None

        def metric(name: str, key: str, unit: str, scale: float = 1.0,
                   positive_is_good: bool = True) -> dict:
            you, peer = mine(key, scale), avg(key, scale)
            vs = round((you - peer) / peer * 100.0, 1) if (you is not None and peer) else None
            return {"metric": name, "you": you, "peer_avg": peer, "vs_peer_pct": vs,
                    "unit": unit, "positive_is_good": positive_is_good}

        metrics = [
            metric("Revenue (LTM)", "revenue_ltm", "usd"),
            metric("Managed Revenue %", "managed_revenue_ratio", "pct", scale=100.0),
            metric("Revenue Growth 3m", "revenue_growth_3m_pct", "pct"),
            metric("AUM", "aum_total", "usd"),
            metric("Households", "household_count", "count"),
            metric("AGP Risk Score", "agp_risk_score", "score", positive_is_good=False),
        ]

        # percentile of this advisor among the peer set by LTM revenue
        my_rev = mine("revenue_ltm") or 0.0
        peer_revs = [float(f["revenue_ltm"]) for f in peer_feats if f.get("revenue_ltm") is not None]
        percentile = round(sum(1 for v in peer_revs if v < my_rev) / len(peer_revs) * 100) if peer_revs else None

        rows = [{"scope_id": advisor_id, "label": self._name("phx_dm_advisor", advisor_id, "advisor_name"),
                 "per_advisor": my_rev, "advisor_count": 1, "is_current": True}]
        for p in peers:
            f = feats_by_peer.get(p["advisor_id"])
            if not f:
                continue
            rows.append({"scope_id": p["advisor_id"], "label": p["advisor_name"],
                         "per_advisor": round(float(f.get("revenue_ltm") or 0.0), 2),
                         "advisor_count": 1, "is_current": False})
        rows.sort(key=lambda r: r["per_advisor"], reverse=True)

        firm_per, _ = self._per_advisor_rev("FIRM", self._firm_id())
        return {
            "peer_type": "Similar Advisor (GNN)",
            "model": model,
            "current_per_advisor": my_rev,
            "current_advisor_count": 1,
            "firm_per_advisor": firm_per,
            "vs_firm_pct": round((my_rev - firm_per) / firm_per * 100, 1) if firm_per else None,
            "percentile": percentile,
            "rows": rows,
            "peers": peers,
            "metrics": metrics,
            "why": (
                f"Peer group = the {len(peers)} nearest advisors by {model} embedding cosine "
                "similarity — learned from the real graph (households, products, CRM, revenue "
                "patterns), not an arbitrary bucket. Scores shown per peer."
            ),
        }

    def _recent_transactions(self, scope_type: str, scope_id: str,
                             advisor_ids: list[str], limit: int = 8) -> list[dict]:
        """Recent Transaction Highlights (mockup bottom-left): the latest real
        revenue transactions in scope with their household + product context, via
        GQ-051 get_scope_transactions. Leadership scopes surface the largest
        recent movers. Per-advisor store traversal only on the logged fallback."""
        results = run_catalog_query(
            self._graph,
            "get_scope_transactions",
            {"scope_type": scope_type.upper(), "scope_id": str(scope_id),
             "start_date": _DATE_MIN, "end_date": _DATE_MAX},
        )
        if results is not None:
            for entry in results:
                txs = entry.get("transactions")
                if txs is None:
                    continue
                ranked = sorted(
                    (t for t in txs),
                    key=lambda t: (str(t.get("attributes", {}).get("transaction_date") or ""),
                                   abs(float(t.get("attributes", {}).get("revenue_amount") or 0.0))),
                    reverse=True,
                )
                out = []
                for t in ranked[:limit]:
                    a = t.get("attributes", {})
                    out.append({
                        "transaction_id": str(t.get("v_id")),
                        "date": str(a.get("transaction_date") or ""),
                        "household": str(a.get("household_name")) if a.get("household_name") else None,
                        "household_id": str(a.get("household_id")) if a.get("household_id") else None,
                        "product": str(a.get("product_name")) if a.get("product_name") else None,
                        "revenue_impact": round(float(a.get("revenue_amount") or 0.0), 2),
                        "type": str(a.get("transaction_type") or "—"),
                        "advisor_name": str(a.get("advisor_name") or ""),
                    })
                return out
        logger.warning("recent transactions for %s/%s using local store traversal fallback",
                       scope_type, scope_id)
        rows: list[dict] = []
        for aid in advisor_ids:
            aname = self._name("phx_dm_advisor", aid, "advisor_name")
            for txid in self._store.in_ids("phx_dm_transaction_for_advisor", aid):
                a = self._store.vertex("phx_dm_revenue_transaction", txid)
                if not a:
                    continue
                rows.append({"txid": txid, "advisor_id": aid, "advisor_name": aname, "attrs": a})
        # newest first; big absolute impact breaks ties (leadership scopes see movers)
        rows.sort(key=lambda r: (str(r["attrs"].get("transaction_date") or ""),
                                 abs(float(r["attrs"].get("revenue_amount") or 0.0))), reverse=True)
        out = []
        for r in rows[:limit]:
            a, txid = r["attrs"], r["txid"]
            hhs = self._store.out_ids("phx_dm_transaction_for_household", txid)
            prods = self._store.out_ids("phx_dm_transaction_for_product", txid)
            out.append({
                "transaction_id": txid,
                "date": str(a.get("transaction_date") or ""),
                "household": self._name("phx_dm_household", hhs[0], "household_name") if hhs else None,
                "household_id": hhs[0] if hhs else None,
                "product": self._name("phx_dm_product", prods[0], "product_name") if prods else None,
                "revenue_impact": round(float(a.get("revenue_amount") or 0.0), 2),
                "type": str(a.get("transaction_type") or "—"),
                "advisor_name": r["advisor_name"],
            })
        return out

    def _benchmark(self, scope_type: str, scope_id: str) -> dict:
        """Revenue-per-advisor of the current scope vs its peer scopes + the firm
        average, with the current scope's percentile. Real values from snapshots.
        ADVISOR scope uses the GNN similarity engine as the peer group (REQ-2)."""
        if scope_type.upper() == "ADVISOR":
            return self._advisor_benchmark(scope_id)
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
        # period passes through so top/bottom advisors rank over the selected window
        rollup = ScopeRollupService().summary(scope_type=st, scope_id=scope_id, period=period)
        revenue = RevenueAnalyticsService().analytics(st, scope_id, period=period)
        markets = self._markets(st, scope_id)
        benchmark = self._benchmark(st, scope_id)
        headline = self._headline(st, scope_id, compare_to, revenue, benchmark)

        # Scope-aware tile set (REQ-1): advisor persona sees their book; leaders see rollups.
        from app.scope.tiles import advisor_tiles, leadership_tiles
        if st == "ADVISOR":
            feats = (self._snaps.latest_for_entity("ADVISOR", scope_id) or {}).get("features", {})
            tiles = advisor_tiles(feats, revenue, headline)
        else:
            tiles = leadership_tiles(rollup["totals"], revenue, headline, rollup["comparison"])

        advisor_ids = resolve_scope_advisor_ids_graph(self._graph, st, scope_id)
        return {
            "scope_type": st,
            "scope_id": scope_id,
            "period": (period or "LTM").upper(),
            "compare_to": compare_to,
            "headline": headline,
            "tiles": tiles,
            "totals": rollup["totals"],
            "comparison": rollup["comparison"],
            "top_advisors": rollup["top_advisors"],
            "bottom_advisors": rollup["bottom_advisors"],
            "child_breakdown": rollup["child_breakdown"],
            "recent_transactions": self._recent_transactions(st, scope_id, advisor_ids),
            "revenue": {
                "monthly_trend": revenue.get("monthly_trend", []),
                "monthly_trend_prior": revenue.get("monthly_trend_prior", []),
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
