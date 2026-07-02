from __future__ import annotations

from fastapi import APIRouter

from app.services.final_audit_service import FinalAuditService
from app.shared.responses import ok

router = APIRouter(prefix="/final-audit", tags=["Final Audit"])


@router.get("/run")
def run_final_audit():
    return ok(data=FinalAuditService().run_audit())
