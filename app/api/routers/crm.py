from fastapi import APIRouter

from app.crm.service import CrmService
from app.shared.responses import ok

router = APIRouter(prefix="/crm", tags=["CRM"])


@router.get("/leads/{advisor_id}")
def leads(advisor_id: str, status: str = "ALL", limit: int = 50):
    return ok(data=CrmService().leads(advisor_id, status, limit))


@router.get("/referrals/{advisor_id}")
def referrals(advisor_id: str, status: str = "ALL", limit: int = 50):
    return ok(data=CrmService().referrals(advisor_id, status, limit))


@router.get("/opportunities/{advisor_id}")
def opportunities(advisor_id: str, status: str = "ALL", limit: int = 50):
    return ok(data=CrmService().opportunities(advisor_id, status, limit))


@router.get("/pipeline/{advisor_id}")
def pipeline(advisor_id: str):
    return ok(data=CrmService().pipeline_by_stage(advisor_id))


@router.get("/work-summary/{advisor_id}")
def work_summary(advisor_id: str):
    return ok(data=CrmService().work_summary(advisor_id))


@router.get("/feature-inputs/{advisor_id}")
def feature_inputs(advisor_id: str):
    return ok(data=CrmService().feature_inputs(advisor_id))
