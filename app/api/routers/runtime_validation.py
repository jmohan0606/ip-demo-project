from __future__ import annotations

from fastapi import APIRouter

from app.services.runtime_validation_service import RuntimeValidationService
from app.shared.responses import ok

router = APIRouter(prefix="/runtime-validation", tags=["Runtime Validation"])


@router.get("/run")
def run_runtime_validation():
    return ok(data=RuntimeValidationService().run())
