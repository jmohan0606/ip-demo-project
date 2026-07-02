from __future__ import annotations

from fastapi import APIRouter

from app.models.features import FeatureMaterializationRequest
from app.services.feature_store_service import FeatureStoreService
from app.shared.responses import ok

router = APIRouter(prefix="/features", tags=["Feature Store"])


@router.post("/materialize")
def materialize(request: FeatureMaterializationRequest):
    return ok(data=[r.model_dump() for r in FeatureStoreService().materialize(request)])


@router.get("/vectors")
def vectors(feature_group: str | None = None, limit: int = 100):
    return ok(data=FeatureStoreService().list_vectors(feature_group, limit))


@router.get("/vector")
def vector(entity_type: str, entity_id: str, feature_group: str):
    return ok(data=FeatureStoreService().get_vector(entity_type, entity_id, feature_group))


@router.get("/counts")
def counts():
    return ok(data=FeatureStoreService().counts())
