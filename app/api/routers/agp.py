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


@router.get("/kpi-scorecard/{advisor_id}")
def kpi_scorecard(advisor_id: str):
    return ok(data=AgpService().kpi_scorecard(advisor_id))


@router.get("/coaching/{advisor_id}")
def coaching_history(advisor_id: str):
    return ok(data=AgpService().coaching_history(advisor_id))


@router.get("/cohort-summary")
def cohort_summary(program_id: str = "AGP24", cohort: str = "ALL", scope_type: str = "FIRM", scope_id: str = "F001"):
    return ok(data=AgpService().cohort_summary(program_id, cohort, scope_type, scope_id))


@router.get("/mentor-pairing")
def mentor_pairing():
    """Section 10 — GNN-similarity constrained mentor/mentee pairing: at-risk enrollees
    matched to healthy, higher-producing advisors with the most similar books (GraphSAGE
    embedding cosine), under real capacity/outperformance constraints."""
    from app.agp.mentorship import AgpMentorshipService
    return ok(data=AgpMentorshipService().mentor_pairing())


@router.get("/program-roi")
def program_roi(window: int = 3, peer_k: int = 5):
    """Section 10 — AGP program ROI with a fair peer baseline: each enrollee's production
    growth since their real enrollment date vs the same calendar-window growth of their
    GNN-most-similar non-enrolled advisors."""
    from app.agp.mentorship import AgpMentorshipService
    return ok(data=AgpMentorshipService().program_roi(window=window, peer_k=peer_k))
