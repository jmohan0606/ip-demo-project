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


@router.get("/as-of/{advisor_id}")
def as_of_snapshot(advisor_id: str, as_of: str):
    """Point-in-time feature snapshot (Section 11.4 temporal KG): recompute the advisor's
    features AS OF a chosen date from the real time-windowed graph facts. Persisted as a
    versioned snapshot (FS_<id>_<date>_<version>), so the feature store accumulates real
    history you can compare across dates."""
    from datetime import date as _date

    y, m, d = (int(p) for p in as_of.split("-"))
    engine = FeatureEngineeringService(as_of=_date(y, m, d))
    snapshot = engine.compute_advisor_snapshot(advisor_id)
    result = engine.persist_snapshot(snapshot)
    return ok(data={**result, "as_of": as_of, "features": snapshot.values(), "lineage": snapshot.lineage()})


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
