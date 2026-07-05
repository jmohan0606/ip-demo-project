from collections import Counter

from fastapi import APIRouter

from app.agp.service import AgpService
from app.ai.insights.structured_view import structured_insight_coaching
from app.crm.service import CrmService
from app.embeddings.similar_entities import _embeddings_by_entity, similar_entities
from app.features.snapshot_store import SnapshotStore
from app.graph.client import get_graph_client
from app.models.insights_coaching import InsightRequest, InsightScopeType
from app.services.insights_coaching_service import InsightsCoachingService
from app.shared.responses import ok

router = APIRouter(prefix="/advisor", tags=["Advisor 360"])


@router.get("/360/{advisor_id}")
def advisor_360(advisor_id: str):
    graph = get_graph_client()
    store = graph.store
    merged: dict = {}
    for entry in graph.run_query("get_advisor_360", {"advisor_id": advisor_id}).get("results", []):
        merged.update(entry)

    # Monthly revenue trend — the SAME GQ-005 data the Revenue Agent reads
    # (transactions aggregated per time period). Charted as a real time series,
    # not a single KPI number.
    revenue_trend: list[dict] = []
    for entry in graph.run_query(
        "get_revenue_trend_by_scope",
        {"scope_type": "ADVISOR", "scope_id": advisor_id, "period_grain": "MONTH"},
    ).get("results", []):
        for row in entry.get("revenue_trend", []):
            if row.get("revenue") is not None:
                revenue_trend.append({
                    "label": row.get("label"),
                    "revenue": round(float(row["revenue"]), 2),
                    "transaction_count": row.get("transaction_count", 0),
                })

    # Book composition by account type — a real categorical breakdown of the
    # book's AUM (households segment is monoculture in the seed, so this is the
    # meaningful donut). Aggregated from the graph accounts already returned.
    mix: dict[str, dict] = {}
    for account in merged.get("accounts", []):
        attrs = account.get("attributes", {})
        acct_type = str(attrs.get("account_type") or "OTHER")
        value = float(attrs.get("current_value") or 0)
        bucket = mix.setdefault(acct_type, {"account_type": acct_type, "value": 0.0, "count": 0})
        bucket["value"] += value
        bucket["count"] += 1
    account_mix = sorted(
        ({**b, "value": round(b["value"], 2)} for b in mix.values()),
        key=lambda b: b["value"],
        reverse=True,
    )

    # Household segment breakdown (count + AUM per segment) — the visual split the
    # households table lacked (CLAUDE.md 9.5).
    seg: dict[str, dict] = {}
    for hh in merged.get("households", []):
        attrs = hh.get("attributes", {})
        segment = str(attrs.get("segment") or attrs.get("tier") or "OTHER")
        value = float(attrs.get("total_aum") or 0)
        bucket = seg.setdefault(segment, {"segment": segment, "aum": 0.0, "count": 0})
        bucket["aum"] += value
        bucket["count"] += 1
    segment_mix = sorted(
        ({**b, "aum": round(b["aum"], 2)} for b in seg.values()),
        key=lambda b: b["count"], reverse=True,
    )

    # CRM execution as outcome-coded cards (won / lost / negotiate / open) — CRM-003.
    crm_opportunities = CrmService().opportunities(advisor_id).get("opportunities", [])

    # Similar households / accounts — extends advisor similarity to other entity
    # types via real cosine NN over persisted embedding vectors (CLAUDE.md 9.5).
    similar: dict = {"households": None, "accounts": None}
    hh_emb = _embeddings_by_entity(store, "HOUSEHOLD")
    acct_emb = _embeddings_by_entity(store, "ACCOUNT")
    adv_hh = [h.get("v_id") for h in merged.get("households", []) if h.get("v_id") in hh_emb]
    adv_acct = [a.get("v_id") for a in merged.get("accounts", []) if a.get("v_id") in acct_emb]
    if adv_hh:
        # focus on the advisor's largest-AUM household that has an embedding
        focus_hh = max(adv_hh, key=lambda h: float((store.vertex("phx_dm_household", h) or {}).get("total_aum") or 0))
        similar["households"] = similar_entities("HOUSEHOLD", focus_hh, 3)
    if adv_acct:
        focus_acct = max(adv_acct, key=lambda a: float((store.vertex("phx_dm_account", a) or {}).get("current_value") or 0))
        similar["accounts"] = similar_entities("ACCOUNT", focus_acct, 3)

    return ok(data={
        "graph": merged,
        "feature_snapshot": SnapshotStore().latest_for_entity("ADVISOR", advisor_id),
        "agp_track": AgpService().track_status(advisor_id),
        "crm_summary": CrmService().work_summary(advisor_id),
        "crm_opportunities": crm_opportunities,
        "revenue_trend": revenue_trend,
        "account_mix": account_mix,
        "segment_mix": segment_mix,
        "similar": similar,
    })


@router.get("/360/{advisor_id}/ai")
def advisor_360_ai(advisor_id: str, persona: str = "Advisor", time_period: str = "LTM"):
    """Structured per-advisor AI Insight Summary (Key Drivers / Watch Outs / What to
    Monitor) and AI Coaching Card (Recommendation / Shoutout / Action Steps /
    Guideline Basis), grounded in the advisor's real features/predictions/opportunities.
    Reuses the Phase-5..9 insight engine; no memory/graph writes (read-only view)."""
    request = InsightRequest(
        scope_type=InsightScopeType.ADVISOR,
        scope_id=advisor_id,
        persona=persona,
        time_period=time_period,
        include_ai_generation=True,
        write_to_memory=False,
        write_to_tigergraph=False,
    )
    payload = InsightsCoachingService().generate_dashboard_payload(request)
    return ok(data=structured_insight_coaching(payload))


@router.get("/list")
def advisor_list():
    merged: dict = {}
    for entry in get_graph_client().run_query(
        "get_scope_descendants", {"scope_type": "ALL", "scope_id": "", "entity_type": "ADVISOR"}
    ).get("results", []):
        merged.update(entry)
    advisors = [
        {"advisor_id": v["v_id"], "advisor_name": v.get("attributes", {}).get("advisor_name")}
        for v in merged.get("advisor_descendants", [])
    ]
    return ok(data={"advisors": sorted(advisors, key=lambda a: a["advisor_id"])})
