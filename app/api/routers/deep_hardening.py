from __future__ import annotations

from fastapi import APIRouter

from app.services.deep_hardening_service import DeepHardeningService
from app.shared.responses import ok

router = APIRouter(prefix="/deep-hardening", tags=["Deep Runtime Hardening"])


@router.get("/run")
def run_deep_hardening():
    return ok(data=DeepHardeningService().run())
