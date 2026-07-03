from fastapi import APIRouter

from app.features.engineering import FeatureEngineeringService
from app.features.snapshot_store import SnapshotStore
from app.shared.responses import ok

router = APIRouter(prefix="/features", tags=["Feature Store"])


@router.post("/compute/{advisor_id}")
def compute_snapshot(advisor_id: str):
    engine = FeatureEngineeringService()
    snapshot = engine.compute_advisor_snapshot(advisor_id)
    result = engine.persist_snapshot(snapshot)
    return ok(data={**result, "features": snapshot.values(), "lineage": snapshot.lineage()})


@router.get("/snapshot/{advisor_id}")
def latest_snapshot(advisor_id: str):
    return ok(data=SnapshotStore().latest_for_entity("ADVISOR", advisor_id))


@router.get("/snapshots")
def list_snapshots(entity_type: str | None = None, limit: int = 100):
    return ok(data=SnapshotStore().list_snapshots(entity_type, limit))


@router.get("/lineage/{snapshot_id}")
def snapshot_lineage(snapshot_id: str):
    snapshot = SnapshotStore().get(snapshot_id)
    return ok(data={"snapshot_id": snapshot_id, "lineage": (snapshot or {}).get("lineage")})
