from __future__ import annotations

from app.graph.client import get_graph_client
from app.graph.queries.common import graph_fallback_store, run_catalog_query

# Curated one-hop neighborhood around a focal advisor: (edge, direction, cap,
# group, node vertex type). Direction "out" = advisor is the edge source, "in" =
# advisor is the target. Caps keep the canvas legible; every node/edge below is a
# REAL vertex/edge from the foundation graph, not a synthesized relationship.
_SPEC = [
    ("phx_dm_advisor_in_market", "out", 1, "org", "phx_dm_market"),
    ("phx_dm_advisor_serves_household", "out", 6, "household", "phx_dm_household"),
    ("phx_dm_advisor_has_crm_opportunity", "out", 3, "crm", "phx_dm_crm_opportunity"),
    ("phx_dm_advisor_has_crm_lead", "out", 3, "crm", "phx_dm_crm_lead"),
    ("phx_dm_advisor_has_agp_enrollment", "out", 1, "agp", "phx_dm_agp_enrollment"),
    ("phx_dm_advisor_has_goal", "out", 1, "agp", "phx_dm_agp_goal"),
    ("phx_dm_prediction_for_advisor", "in", 1, "ai", "phx_dm_prediction"),
    ("phx_dm_opportunity_for_advisor", "in", 1, "ai", "phx_dm_opportunity"),
    ("phx_dm_recommendation_for_advisor", "in", 1, "ai", "phx_dm_recommendation"),
]

# human-readable edge verbs
_VERB = {
    "phx_dm_advisor_in_market": "in market",
    "phx_dm_advisor_serves_household": "serves",
    "phx_dm_advisor_has_crm_opportunity": "CRM opportunity",
    "phx_dm_advisor_has_crm_lead": "CRM lead",
    "phx_dm_advisor_has_agp_enrollment": "enrolled in",
    "phx_dm_advisor_has_goal": "has goal",
    "phx_dm_prediction_for_advisor": "predicted for",
    "phx_dm_opportunity_for_advisor": "opportunity for",
    "phx_dm_recommendation_for_advisor": "recommended for",
}


def _label(attrs: dict, vid: str) -> str:
    if not attrs:
        return vid
    for key, value in attrs.items():
        if key.endswith("_name") and value:
            return str(value)
    for key in ("title", "description", "opportunity_type", "lead_source", "program_name", "status"):
        if attrs.get(key):
            return str(attrs[key])[:40]
    return vid


# Creation-date attribute per vertex type — for the temporal "as-of" traversal (Section 11.4).
# A node is hidden when its creation date is AFTER the as-of date (it didn't exist yet). Nodes
# with no creation date are structural and always shown.
_DATE_KEYS = {
    "phx_dm_crm_lead": "created_date",
    "phx_dm_crm_referral": "created_at",
    "phx_dm_agp_enrollment": "start_date",
    "phx_dm_recommendation": "generated_at",
    "phx_dm_prediction_result": "generated_at",
    "phx_dm_opportunity": "generated_at",
}


# GQ-009 get_advisor_360 result-set key per _SPEC edge (all one-hop from the advisor).
# phx_dm_advisor_has_goal is the one edge GQ-009 does not traverse — it is served by
# GQ-013 get_agp_enrollment_summary's `goals` set instead.
_GQ009_SET = {
    "phx_dm_advisor_in_market": "market",
    "phx_dm_advisor_serves_household": "households",
    "phx_dm_advisor_has_crm_opportunity": "crm_opportunities",
    "phx_dm_advisor_has_crm_lead": "crm_leads",
    "phx_dm_advisor_has_agp_enrollment": "enrollments",
    "phx_dm_prediction_for_advisor": "predictions",
    "phx_dm_opportunity_for_advisor": "opportunities",
    "phx_dm_recommendation_for_advisor": "recommendations",
}


def _neighbors_via_queries(graph, advisor_id: str):
    """Fetch the focal advisor + per-edge neighbor rows via installed catalog queries
    (GQ-009 get_advisor_360 for eight of the nine _SPEC edges, GQ-013
    get_agp_enrollment_summary for phx_dm_advisor_has_goal). Returns
    (adv_attrs, {edge: [(vid, attrs), ...]}) or None when the graph query path failed —
    the caller then uses the original local-store traversal (logged fallback)."""
    results = run_catalog_query(graph, "get_advisor_360", {"advisor_id": advisor_id})
    if not results:
        return None
    entry = results[0]

    def rows(vset) -> list[tuple[str, dict]]:
        out = []
        for row in vset or []:
            vid = str(row.get("v_id") or "")
            if vid:
                out.append((vid, row.get("attributes") or {}))
        return out

    advisor_rows = rows(entry.get("advisor"))
    adv_attrs = advisor_rows[0][1] if advisor_rows else {}

    neighbors: dict[str, list[tuple[str, dict]]] = {
        edge: rows(entry.get(set_key)) for edge, set_key in _GQ009_SET.items()
    }

    goal_results = run_catalog_query(
        graph, "get_agp_enrollment_summary", {"advisor_id": advisor_id}
    )
    if goal_results:
        neighbors["phx_dm_advisor_has_goal"] = rows(goal_results[0].get("goals"))
    else:
        # GQ-013 failed while GQ-009 succeeded — serve just the goal edge from the
        # local store (run_catalog_query already logged the fallback warning).
        store = graph_fallback_store(graph)
        neighbors["phx_dm_advisor_has_goal"] = [
            (vid, store.vertex("phx_dm_goal", vid) or {})
            for vid in store.out_ids("phx_dm_advisor_has_goal", advisor_id)
        ]
    return adv_attrs, neighbors


def advisor_neighborhood(advisor_id: str, as_of: str | None = None) -> dict:
    """Real one-hop subgraph around an advisor for the graph explorer canvas. With `as_of`
    (YYYY-MM-DD), only entities that existed on that date are included — a temporal traversal
    showing how the advisor's graph (esp. the AI pipeline artifacts) grew over time."""
    graph = get_graph_client()
    fetched = _neighbors_via_queries(graph, advisor_id)
    if fetched is not None:
        adv_attrs, neighbor_map = fetched
    else:
        # fallback: original local-store traversal (reached only when the catalog
        # queries returned None; run_catalog_query already logged the warning)
        store = graph_fallback_store(graph)
        adv_attrs = store.vertex("phx_dm_advisor", advisor_id) or {}
        neighbor_map = {}
        for edge, direction, _cap, _group, vtype in _SPEC:
            neighbor_ids = (
                store.out_ids(edge, advisor_id)
                if direction == "out"
                else store.in_ids(edge, advisor_id)
            )
            neighbor_map[edge] = [
                (vid, store.vertex(vtype, vid) or {}) for vid in neighbor_ids
            ]
    focal_label = str(adv_attrs.get("advisor_name") or advisor_id)

    nodes = [{
        "id": advisor_id,
        "type": "Advisor",
        "group": "advisor",
        "label": focal_label,
        "attributes": adv_attrs,
    }]
    edges = []
    seen = {advisor_id}
    hidden = 0

    for edge, direction, cap, group, vtype in _SPEC:
        for vid, attrs in list(neighbor_map.get(edge, []))[:cap]:
            if as_of:
                date_key = _DATE_KEYS.get(vtype)
                created = str(attrs.get(date_key, "")) if date_key else ""
                if created and created[:10] > as_of:
                    hidden += 1
                    continue
            if vid not in seen:
                nodes.append({
                    "id": vid,
                    "type": vtype.replace("phx_dm_", "").replace("_", " ").title(),
                    "group": group,
                    "label": _label(attrs, vid),
                    "attributes": attrs,
                })
                seen.add(vid)
            src, tgt = (advisor_id, vid) if direction == "out" else (vid, advisor_id)
            edges.append({"source": src, "target": tgt, "label": _VERB.get(edge, edge)})

    return {
        "focal_advisor": {"id": advisor_id, "label": focal_label},
        "as_of": as_of,
        "nodes": nodes,
        "edges": edges,
        "counts": {"nodes": len(nodes), "edges": len(edges), "hidden_by_as_of": hidden},
        "evidence": {
            "source": "foundation graph one-hop traversal from phx_dm_advisor"
                      + (f" · point-in-time as of {as_of}" if as_of else ""),
            "edges_traversed": [s[0] for s in _SPEC],
        },
    }
