from __future__ import annotations

from fastapi import APIRouter

from app.services.demo_data_catalog_service import DemoDataCatalogService
from app.shared.responses import ok

router = APIRouter(prefix="/demo-data", tags=["Demo Data"])


@router.get("/manifest")
def manifest():
    return ok(data=DemoDataCatalogService().manifest())


@router.get("/files")
def files():
    return ok(data=DemoDataCatalogService().list_csv_files())
