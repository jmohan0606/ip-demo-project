from __future__ import annotations

from fastapi import APIRouter

from app.ingestion.ingestion_service import IngestionService
from app.models.ingestion import IngestionRunRequest
from app.shared.responses import ok

router = APIRouter(prefix="/ingestion", tags=["Ingestion"])


@router.get("/entities")
def entities():
    return ok(data=IngestionService().list_entities())


@router.get("/batches")
def batches():
    return ok(data=IngestionService().list_batches())


@router.post("/run")
def run_ingestion(request: IngestionRunRequest):
    response = IngestionService().run_entity_ingestion(request)
    return ok(data=response.model_dump())
