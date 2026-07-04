from __future__ import annotations

from app.graph.client import get_graph_client

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


def advisor_neighborhood(advisor_id: str) -> dict:
    """Real one-hop subgraph around an advisor for the graph explorer canvas."""
    store = get_graph_client().store
    adv_attrs = store.vertex("phx_dm_advisor", advisor_id) or {}
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

    for edge, direction, cap, group, vtype in _SPEC:
        neighbor_ids = (
            store.out_ids(edge, advisor_id) if direction == "out" else store.in_ids(edge, advisor_id)
        )
        for vid in list(neighbor_ids)[:cap]:
            attrs = store.vertex(vtype, vid) or {}
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
        "nodes": nodes,
        "edges": edges,
        "counts": {"nodes": len(nodes), "edges": len(edges)},
        "evidence": {
            "source": "foundation graph one-hop traversal from phx_dm_advisor",
            "edges_traversed": [s[0] for s in _SPEC],
        },
    }
