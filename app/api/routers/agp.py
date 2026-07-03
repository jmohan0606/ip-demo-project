from fastapi import APIRouter

from app.agp.service import AgpService
from app.shared.responses import ok

router = APIRouter(prefix="/agp", tags=["AGP Program"])


@router.get("/enrollment/{advisor_id}")
def enrollment_summary(advisor_id: str):
    return ok(data=AgpService().enrollment_summary(advisor_id))


@router.get("/milestones/{enrollment_id}")
def milestone_timeline(enrollment_id: str):
    return ok(data=AgpService().milestone_timeline(enrollment_id))


@router.get("/track-status/{advisor_id}")
def track_status(advisor_id: str):
    return ok(data=AgpService().track_status(advisor_id))


@router.get("/coaching/{advisor_id}")
def coaching_history(advisor_id: str):
    return ok(data=AgpService().coaching_history(advisor_id))


@router.get("/cohort-summary")
def cohort_summary(program_id: str = "AGP24", cohort: str = "ALL", scope_type: str = "FIRM", scope_id: str = "F001"):
    return ok(data=AgpService().cohort_summary(program_id, cohort, scope_type, scope_id))
