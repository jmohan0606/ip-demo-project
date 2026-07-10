"""Section 10 — real global search + real notifications (the two flagged header icons).

Search: across advisors / households / knowledge documents by name or id.
Notifications: a real feed derived from data — at-risk advisors, AGP off-track,
overdue CRM follow-ups — not a decorative bell.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.graph.client import get_graph_client
from app.graph.queries.common import graph_fallback_store, run_catalog_query
from app.features.snapshot_store import SnapshotStore
from app.shared.responses import ok

router = APIRouter(prefix="/search", tags=["Search & Notifications"])


def _scope_descendants_rows(graph, entity_type: str) -> dict[str, list[dict]] | None:
    """All advisors/households via the installed GQ-002 get_scope_descendants
    query (scope ALL). Returns {"advisors": [...], "households": [...]} of
    RESTPP-style rows, or None when the query is unavailable — callers then use
    the logged local-store fallback."""
    results = run_catalog_query(
        graph,
        "get_scope_descendants",
        {"scope_type": "ALL", "scope_id": "ALL", "entity_type": entity_type},
    )
    if results is None:
        return None
    for entry in results:
        advisors = entry.get("advisor_descendants")
        households = entry.get("household_descendants")
        if advisors is not None or households is not None:
            return {"advisors": advisors or [], "households": households or []}
    return None


@router.get("/global")
def global_search(q: str = "", limit: int = 8):
    """Real global search across advisors, households and knowledge documents."""
    query = (q or "").strip().lower()
    results: list[dict] = []
    if not query:
        return ok(data={"query": q, "results": []})
    graph = get_graph_client()

    rows = _scope_descendants_rows(graph, "ALL")
    if rows is not None:
        advisor_items = [(str(r.get("v_id")), r.get("attributes", {})) for r in rows["advisors"]]
        household_items = [(str(r.get("v_id")), r.get("attributes", {})) for r in rows["households"]]
    else:
        # fallback: original local-store traversal (run_catalog_query already logged it)
        store = graph_fallback_store(graph)
        advisor_items = list(store.all_vertices("phx_dm_advisor").items())
        household_items = list(store.all_vertices("phx_dm_household").items())

    for aid, attrs in advisor_items:
        name = str(attrs.get("advisor_name") or "")
        if query in name.lower() or query in aid.lower():
            results.append({"type": "Advisor", "id": aid, "label": name or aid,
                            "sublabel": aid, "href": "/advisor-360"})
        if len(results) >= limit:
            break
    for hid, attrs in household_items:
        if len(results) >= limit:
            break
        name = str(attrs.get("household_name") or "")
        if query in name.lower() or query in hid.lower():
            results.append({"type": "Household", "id": hid, "label": name or hid,
                            "sublabel": f"{attrs.get('segment', '')} · {hid}", "href": "/client-360"})
    # knowledge documents via GQ-058 get_documents (run_query); the local store
    # scan survives only as the logged fallback. Title matching stays client-side.
    try:
        doc_rows = run_catalog_query(graph, "get_documents", {"result_limit": 1000})
        doc_items: list[tuple[str, dict]] | None = None
        if doc_rows is not None:
            for entry in doc_rows:
                if entry.get("documents") is not None:
                    doc_items = [(str(r.get("v_id")), r.get("attributes", {})) for r in entry["documents"]]
                    break
        if doc_items is None:
            # fallback: original local-store traversal (run_catalog_query already logged it)
            doc_items = list(graph_fallback_store(graph).all_vertices("phx_dm_document").items())
        for did, attrs in doc_items:
            if len(results) >= limit:
                break
            title = str(attrs.get("title") or attrs.get("document_name") or "")
            if query in title.lower():
                results.append({"type": "Document", "id": did, "label": title,
                                "sublabel": "Knowledge base", "href": "/knowledge"})
    except Exception:
        pass
    return ok(data={"query": q, "results": results[:limit]})


@router.get("/notifications")
def notifications(limit: int = 12):
    """Real notification feed derived from live data: AGP off-track / at-risk
    advisors and overdue CRM follow-ups. Severity-tagged for the header bell."""
    graph = get_graph_client()
    snaps = SnapshotStore()
    items: list[dict] = []

    # Advisor enumeration via GQ-002 (scope ALL). GQ-035 get_notifications_for_user was
    # considered and rejected: it reads stored phx_dm_notification vertices for a given
    # user_id, while this feed is derived live from advisor feature snapshots.
    rows = _scope_descendants_rows(graph, "ADVISOR")
    if rows is not None:
        advisor_items = [(str(r.get("v_id")), r.get("attributes", {})) for r in rows["advisors"]]
    else:
        # fallback: original local-store traversal (run_catalog_query already logged it)
        advisor_items = list(graph_fallback_store(graph).all_vertices("phx_dm_advisor").items())

    for aid, attrs in advisor_items:
        snap = snaps.latest_for_entity("ADVISOR", aid)
        f = (snap or {}).get("features", {}) if snap else {}
        name = str(attrs.get("advisor_name") or aid)
        risk = f.get("agp_risk_score")
        if risk is not None and float(risk) >= 70:
            items.append({"severity": "critical" if float(risk) >= 85 else "urgent",
                          "type": "AGP Risk", "title": f"{name} is off-track",
                          "detail": f"AGP risk score {round(float(risk), 1)} — needs coaching intervention.",
                          "advisor_id": aid, "href": "/agp"})
        overdue = f.get("overdue_followup_count")
        if overdue is not None and int(overdue) >= 3:
            items.append({"severity": "attention", "type": "CRM", "title": f"{name}: {int(overdue)} overdue follow-ups",
                          "detail": "CRM execution is slipping — stalled deals to advance.",
                          "advisor_id": aid, "href": "/crm-activities"})
    order = {"critical": 0, "urgent": 1, "attention": 2}
    items.sort(key=lambda x: order.get(x["severity"], 3))
    return ok(data={"count": len(items), "items": items[:limit]})
