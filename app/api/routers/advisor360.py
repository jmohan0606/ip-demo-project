from fastapi import APIRouter

from app.agp.service import AgpService
from app.crm.service import CrmService
from app.features.snapshot_store import SnapshotStore
from app.graph.client import get_graph_client
from app.shared.responses import ok

router = APIRouter(prefix="/advisor", tags=["Advisor 360"])


@router.get("/360/{advisor_id}")
def advisor_360(advisor_id: str):
    merged: dict = {}
    for entry in get_graph_client().run_query("get_advisor_360", {"advisor_id": advisor_id}).get("results", []):
        merged.update(entry)
    return ok(data={
        "graph": merged,
        "feature_snapshot": SnapshotStore().latest_for_entity("ADVISOR", advisor_id),
        "agp_track": AgpService().track_status(advisor_id),
        "crm_summary": CrmService().work_summary(advisor_id),
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
