from fastapi import APIRouter

from app.agp.service import AgpService
from app.crm.service import CrmService
from app.features.snapshot_store import SnapshotStore
from app.graph.client import get_graph_client
from app.shared.responses import ok

router = APIRouter(prefix="/advisor", tags=["Advisor 360"])


@router.get("/360/{advisor_id}")
def advisor_360(advisor_id: str):
    graph = get_graph_client()
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

    return ok(data={
        "graph": merged,
        "feature_snapshot": SnapshotStore().latest_for_entity("ADVISOR", advisor_id),
        "agp_track": AgpService().track_status(advisor_id),
        "crm_summary": CrmService().work_summary(advisor_id),
        "revenue_trend": revenue_trend,
        "account_mix": account_mix,
    })


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
