"""Multi-hop relational reasoning by REAL graph traversal (temporal knowledge graph).

These mock-query implementations walk the actual loaded graph (FoundationGraphStore) hop by
hop and record the exact path taken — the entities visited and the edges walked — so the
answer is grounded in traversed relationships, never a flat lookup or an LLM-narrated path.
The `path` each returns is the real, instrumented traversal (from_id → to_ids over a named
edge), surfaced in the Explainability Explorer.

Registered via @mock_query so get_graph_client().run_query(...) dispatches to them in mock mode;
the GSQL equivalents (GQ-048..050) mirror the same traversal for real TigerGraph.
"""

from __future__ import annotations

from app.graph.client import mock_query
from app.graph.foundation_store import FoundationGraphStore


def _name(store, vtype, vid, attr):
    return str((store.vertex(vtype, vid) or {}).get(attr) or vid)


def _advisor_success_signal(store: FoundationGraphStore, advisor_id: str) -> dict:
    """What has worked / is being pursued for this advisor — by traversal:
      recommendations (proven = COMPLETED/ACCEPTED; else pursued) grouped by family,
      recorded impact-ledger entries (real completions), and positive outcome events
      reached via recommendation → feedback → outcome."""
    families: dict[str, dict] = {}
    for rid in store.in_ids("phx_dm_recommendation_for_advisor", advisor_id):
        rv = store.vertex("phx_dm_recommendation", rid) or {}
        fam = rv.get("recommendation_type") or "GENERAL"
        status = str(rv.get("status") or "PRESENTED")
        proven = status in ("COMPLETED", "ACCEPTED", "IN_PROGRESS")
        f = families.setdefault(fam, {"family": fam, "proven": 0, "pursued": 0, "impact": 0.0, "examples": []})
        f["proven" if proven else "pursued"] += 1
        f["impact"] += float(rv.get("estimated_revenue_impact") or 0.0)
        if len(f["examples"]) < 3:
            f["examples"].append({"recommendation_id": rid, "title": rv.get("title"), "status": status})
        # positive outcomes reached via feedback chain (rec → feedback → outcome)
        for fb in store.in_ids("phx_dm_feedback_for_recommendation", rid):
            for oid in store.in_ids("phx_dm_outcome_for_feedback", fb):
                ov = store.vertex("phx_dm_outcome_event", oid) or {}
                if str(ov.get("outcome_type") or "").upper() in ("REVENUE_IMPACT", "ACTION_TAKEN"):
                    f["proven"] += 1
    for lid in store.in_ids("phx_dm_impact_for_advisor", advisor_id):
        lv = store.vertex("phx_dm_impact_ledger", lid) or {}
        fam = lv.get("action_family") or "GENERAL"
        f = families.setdefault(fam, {"family": fam, "proven": 0, "pursued": 0, "impact": 0.0, "examples": []})
        f["proven"] += 1
        f["impact"] += float(lv.get("impact_amount") or 0.0)
    return families


@mock_query("advisor_reasoning_traversal")
def advisor_reasoning_traversal(store: FoundationGraphStore, params: dict) -> list[dict]:
    """"What should I do for advisor X?" answered by walking relationships:
      X → households → open opportunities (what X needs)
      X → similarity_match → similar advisors (with scores) → their successful action families
    Returns the traversed evidence + the exact path (hops with entities visited)."""
    advisor_id = str(params.get("advisor_id") or "")
    limit_similar = int(params.get("similar_limit") or 3)
    path: list[dict] = []
    adv_name = _name(store, "phx_dm_advisor", advisor_id, "advisor_name")

    # Hop 1: advisor → households
    hh_ids = store.out_ids("phx_dm_advisor_serves_household", advisor_id)
    path.append({"hop": 1, "edge": "phx_dm_advisor_serves_household", "from": advisor_id,
                 "to": hh_ids, "description": f"{adv_name} serves {len(hh_ids)} households"})

    # Hop 2: households → open opportunities (what this advisor needs to act on)
    households = []
    for h in hh_ids:
        opp_ids = store.in_ids("phx_dm_opportunity_for_household", h)
        open_opps = []
        for o in opp_ids:
            ov = store.vertex("phx_dm_opportunity", o) or {}
            if str(ov.get("status") or "OPEN").upper() != "ADDRESSED":
                open_opps.append({"opportunity_id": o, "type": ov.get("opportunity_type"),
                                  "severity": ov.get("severity"), "value": ov.get("estimated_value")})
        households.append({"household_id": h, "name": _name(store, "phx_dm_household", h, "household_name"),
                           "open_opportunities": open_opps})
    total_opps = sum(len(h["open_opportunities"]) for h in households)
    path.append({"hop": 2, "edge": "phx_dm_opportunity_for_household", "from": f"{len(hh_ids)} households",
                 "to": [o["opportunity_id"] for h in households for o in h["open_opportunities"]],
                 "description": f"{total_opps} open opportunities across the advisor's households"})

    # Hop 3: advisor → similarity matches → similar advisors (with scores)
    match_ids = store.out_ids("phx_dm_advisor_has_similarity_match", advisor_id)
    similar = []
    for m in match_ids:
        mv = store.vertex("phx_dm_similarity_match", m) or {}
        for tgt in store.out_ids("phx_dm_similarity_match_targets_advisor", m):
            similar.append({"advisor_id": tgt, "name": _name(store, "phx_dm_advisor", tgt, "advisor_name"),
                            "similarity_score": float(mv.get("similarity_score") or 0.0), "match_id": m})
    similar.sort(key=lambda s: s["similarity_score"], reverse=True)
    similar = similar[:limit_similar]
    path.append({"hop": 3, "edge": "phx_dm_advisor_has_similarity_match → similarity_match_targets_advisor",
                 "from": advisor_id, "to": [s["advisor_id"] for s in similar],
                 "description": f"{len(similar)} most-similar advisors (GNN/similarity, scores {[round(s['similarity_score'],2) for s in similar]})"})

    # Hop 4: similar advisors → their successful action families (what worked for peers)
    peer_success: dict[str, dict] = {}
    for s in similar:
        fams = _advisor_success_signal(store, s["advisor_id"])
        s["successful_families"] = sorted(
            ({"family": k, "proven": v["proven"], "pursued": v["pursued"], "impact": round(v["impact"], 0),
              "examples": v["examples"]} for k, v in fams.items()),
            key=lambda x: (x["proven"], x["impact"]), reverse=True)
        for k, v in fams.items():
            agg = peer_success.setdefault(k, {"family": k, "peer_advisors": 0, "proven": 0, "total_impact": 0.0})
            agg["peer_advisors"] += 1
            agg["proven"] += v["proven"]
            agg["total_impact"] += v["impact"]
    path.append({"hop": 4, "edge": "recommendation_for_advisor / impact_for_advisor (per similar advisor)",
                 "from": [s["advisor_id"] for s in similar], "to": list(peer_success.keys()),
                 "description": f"successful action families among similar advisors: {list(peer_success.keys())}"})

    ranked = sorted(peer_success.values(), key=lambda x: (x["proven"], x["total_impact"]), reverse=True)
    return [{
        "advisor_id": advisor_id, "advisor_name": adv_name,
        "households": households, "total_open_opportunities": total_opps,
        "similar_advisors": similar,
        "peer_success_patterns": [{"family": r["family"], "peer_advisors": r["peer_advisors"],
                                   "proven": r["proven"], "total_impact": round(r["total_impact"], 0)} for r in ranked],
        "path": path,
        "hops": len(path),
    }]


@mock_query("scope_reasoning_traversal")
def scope_reasoning_traversal(store: FoundationGraphStore, params: dict) -> list[dict]:
    """A division/market rollup question answered by traversing the scope subgraph:
      scope → advisors → households → real outcomes (open opportunities, recorded impact),
    aggregated with the real contributing entities named."""
    from app.graph.queries.common import resolve_scope_advisor_ids

    scope_type = str(params.get("scope_type") or "FIRM").upper()
    scope_id = str(params.get("scope_id") or "")
    advisor_ids = resolve_scope_advisor_ids(store, scope_type, scope_id)
    path: list[dict] = [{"hop": 1, "edge": f"resolve scope {scope_type} {scope_id} → advisors",
                         "from": scope_id, "to": advisor_ids[:20],
                         "description": f"{len(advisor_ids)} advisors under {scope_type} {scope_id}"}]

    contributors = []
    all_hh = 0
    total_open_opps = 0
    for a in advisor_ids:
        hh = store.out_ids("phx_dm_advisor_serves_household", a)
        all_hh += len(hh)
        open_opps = 0
        for h in hh:
            for o in store.in_ids("phx_dm_opportunity_for_household", h):
                ov = store.vertex("phx_dm_opportunity", o) or {}
                if str(ov.get("status") or "OPEN").upper() != "ADDRESSED":
                    open_opps += 1
        impact = sum(float((store.vertex("phx_dm_impact_ledger", lid) or {}).get("impact_amount") or 0.0)
                     for lid in store.in_ids("phx_dm_impact_for_advisor", a))
        total_open_opps += open_opps
        contributors.append({"advisor_id": a, "name": _name(store, "phx_dm_advisor", a, "advisor_name"),
                             "households": len(hh), "open_opportunities": open_opps, "recorded_impact": round(impact, 0)})
    path.append({"hop": 2, "edge": "advisor_serves_household → opportunity_for_household",
                 "from": f"{len(advisor_ids)} advisors", "to": f"{all_hh} households",
                 "description": f"{all_hh} households, {total_open_opps} open opportunities across the subgraph"})

    contributors.sort(key=lambda c: c["open_opportunities"], reverse=True)
    return [{
        "scope_type": scope_type, "scope_id": scope_id,
        "advisor_count": len(advisor_ids), "household_count": all_hh, "total_open_opportunities": total_open_opps,
        "top_contributors": contributors[:8],
        "path": path, "hops": len(path),
    }]


@mock_query("get_reasoning_traces_for_scope")
def get_reasoning_traces_for_scope(store: FoundationGraphStore, params: dict) -> list[dict]:
    """Prior reasoning traces for an advisor/scope, by traversing phx_dm_reasoning_for_advisor
    (newest first) — the 'experience memory' an agent builds on instead of starting cold."""
    scope_id = str(params.get("scope_id") or "")
    limit = int(params.get("result_limit") or 5)
    trace_ids = store.in_ids("phx_dm_reasoning_for_advisor", scope_id)
    rows = []
    for tid in trace_ids:
        tv = store.vertex("phx_dm_reasoning_trace", tid)
        if tv:
            rows.append({"reasoning_id": tid, **tv})
    rows.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
    return rows[:limit]
