import json
from pathlib import Path
from fastapi import APIRouter
from ..config import settings
from ..services.manifest_service import ManifestService

router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])

@router.get("/files")
def files():
    return {"files": [ManifestService().inspect(e) for e in ManifestService().entries()]}

@router.get("/schema")
def schema():
    return json.loads(Path(settings.schema_catalog_path).read_text(encoding="utf-8"))

@router.get("/queries")
def queries():
    return json.loads(Path(settings.query_catalog_path).read_text(encoding="utf-8"))
