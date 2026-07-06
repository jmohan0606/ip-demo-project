"""Section 10 — real global search + real notifications (the two flagged header icons).

Search: across advisors / households / knowledge documents by name or id.
Notifications: a real feed derived from data — at-risk advisors, AGP off-track,
overdue CRM follow-ups — not a decorative bell.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.graph.client import get_graph_client
from app.features.snapshot_store import SnapshotStore
from app.shared.responses import ok

router = APIRouter(prefix="/search", tags=["Search & Notifications"])


@router.get("/global")
def global_search(q: str = "", limit: int = 8):
    """Real global search across advisors, households and knowledge documents."""
    query = (q or "").strip().lower()
    results: list[dict] = []
    if not query:
        return ok(data={"query": q, "results": []})
    store = get_graph_client().store

    for aid, attrs in store.all_vertices("phx_dm_advisor").items():
        name = str(attrs.get("advisor_name") or "")
        if query in name.lower() or query in aid.lower():
            results.append({"type": "Advisor", "id": aid, "label": name or aid,
                            "sublabel": aid, "href": "/advisor-360"})
        if len(results) >= limit:
            break
    for hid, attrs in store.all_vertices("phx_dm_household").items():
        if len(results) >= limit:
            break
        name = str(attrs.get("household_name") or "")
        if query in name.lower() or query in hid.lower():
            results.append({"type": "Household", "id": hid, "label": name or hid,
                            "sublabel": f"{attrs.get('segment', '')} · {hid}", "href": "/client-360"})
    # knowledge documents
    try:
        for did, attrs in list(store.all_vertices("phx_dm_document").items()):
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
    store = get_graph_client().store
    snaps = SnapshotStore()
    items: list[dict] = []

    for aid, attrs in store.all_vertices("phx_dm_advisor").items():
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
