from __future__ import annotations

from app.graph.client import mock_query
from app.graph.foundation_store import FoundationGraphStore
from app.graph.queries.common import ADVISOR, resolve_scope_advisor_ids, vset


@mock_query("get_agp_enrollment_summary")
def get_agp_enrollment_summary(store: FoundationGraphStore, params: dict) -> list[dict]:
    advisor_id = str(params.get("advisor_id") or "")
    enrollment_ids = store.out_ids("phx_dm_advisor_has_agp_enrollment", advisor_id)
    program_ids: list[str] = []
    progress_ids: list[str] = []
    for enrollment_id in enrollment_ids:
        program_ids.extend(store.out_ids("phx_dm_enrollment_in_agp_program", enrollment_id))
        progress_ids.extend(store.out_ids("phx_dm_enrollment_has_milestone_progress", enrollment_id))
    milestone_ids: list[str] = []
    for progress_id in progress_ids:
        milestone_ids.extend(store.out_ids("phx_dm_progress_for_milestone", progress_id))
    return [
        {
            "advisor": vset(store, ADVISOR, [advisor_id]),
            "enrollments": vset(store, "phx_dm_agp_enrollment", enrollment_ids),
            "programs": vset(store, "phx_dm_agp_program", program_ids),
            "progress": vset(store, "phx_dm_agp_milestone_progress", progress_ids),
            "milestones": vset(store, "phx_dm_agp_milestone", milestone_ids),
            "goals": vset(store, "phx_dm_goal", store.out_ids("phx_dm_advisor_has_goal", advisor_id)),
            "kpis": vset(store, "phx_dm_kpi", store.out_ids("phx_dm_advisor_has_kpi", advisor_id)),
        }
    ]


@mock_query("get_agp_milestone_timeline")
def get_agp_milestone_timeline(store: FoundationGraphStore, params: dict) -> list[dict]:
    enrollment_id = str(params.get("enrollment_id") or "")
    progress_ids = store.out_ids("phx_dm_enrollment_has_milestone_progress", enrollment_id)
    milestone_ids: list[str] = []
    measurement_ids: list[str] = []
    for progress_id in progress_ids:
        milestone_ids.extend(store.out_ids("phx_dm_progress_for_milestone", progress_id))
        measurement_ids.extend(store.out_ids("phx_dm_progress_has_kpi_measurement", progress_id))
    kpi_ids: list[str] = []
    for measurement_id in measurement_ids:
        kpi_ids.extend(store.out_ids("phx_dm_measurement_for_kpi", measurement_id))
    return [
        {
            "enrollment": vset(store, "phx_dm_agp_enrollment", [enrollment_id]),
            "progress": vset(store, "phx_dm_agp_milestone_progress", progress_ids),
            "milestones": vset(store, "phx_dm_agp_milestone", milestone_ids),
            "measurements": vset(store, "phx_dm_agp_kpi_measurement", measurement_ids),
            "kpis": vset(store, "phx_dm_kpi", kpi_ids),
        }
    ]


@mock_query("get_agp_kpi_measurements")
def get_agp_kpi_measurements(store: FoundationGraphStore, params: dict) -> list[dict]:
    enrollment_id = str(params.get("enrollment_id") or "")
    milestone_id = str(params.get("milestone_id") or "")
    all_progress = store.out_ids("phx_dm_enrollment_has_milestone_progress", enrollment_id)
    selected_progress = [
        progress_id
        for progress_id in all_progress
        if not milestone_id
        or milestone_id in store.out_ids("phx_dm_progress_for_milestone", progress_id)
    ]
    milestone_ids: list[str] = []
    measurement_ids: list[str] = []
    for progress_id in selected_progress:
        milestone_ids.extend(store.out_ids("phx_dm_progress_for_milestone", progress_id))
        measurement_ids.extend(store.out_ids("phx_dm_progress_has_kpi_measurement", progress_id))
    kpi_ids: list[str] = []
    for measurement_id in measurement_ids:
        kpi_ids.extend(store.out_ids("phx_dm_measurement_for_kpi", measurement_id))
    return [
        {
            "enrollment": vset(store, "phx_dm_agp_enrollment", [enrollment_id]),
            "milestone_progress": vset(store, "phx_dm_agp_milestone_progress", selected_progress),
            "milestones": vset(store, "phx_dm_agp_milestone", milestone_ids),
            "measurements": vset(store, "phx_dm_agp_kpi_measurement", measurement_ids),
            "kpis": vset(store, "phx_dm_kpi", kpi_ids),
        }
    ]


@mock_query("get_agp_coaching_history")
def get_agp_coaching_history(store: FoundationGraphStore, params: dict) -> list[dict]:
    advisor_id = str(params.get("advisor_id") or "")
    enrollment_ids = store.out_ids("phx_dm_advisor_has_agp_enrollment", advisor_id)
    enrollment_coaching: list[str] = []
    enrollment_reviews: list[str] = []
    for enrollment_id in enrollment_ids:
        enrollment_coaching.extend(store.in_ids("phx_dm_coaching_for_enrollment", enrollment_id))
        enrollment_reviews.extend(store.in_ids("phx_dm_review_for_enrollment", enrollment_id))
    return [
        {
            "advisor": vset(store, ADVISOR, [advisor_id]),
            "enrollments": vset(store, "phx_dm_agp_enrollment", enrollment_ids),
            "coaching": vset(store, "phx_dm_coaching_session", store.in_ids("phx_dm_coaching_for_advisor", advisor_id)),
            "enrollment_coaching": vset(store, "phx_dm_coaching_session", enrollment_coaching),
            "reviews": vset(store, "phx_dm_manager_review", store.in_ids("phx_dm_review_for_advisor", advisor_id)),
            "enrollment_reviews": vset(store, "phx_dm_manager_review", enrollment_reviews),
        }
    ]


@mock_query("get_agp_crm_work_summary")
def get_agp_crm_work_summary(store: FoundationGraphStore, params: dict) -> list[dict]:
    advisor_id = str(params.get("advisor_id") or "")
    lead_ids = store.out_ids("phx_dm_advisor_has_crm_lead", advisor_id)
    referral_ids = store.out_ids("phx_dm_advisor_has_crm_referral", advisor_id)
    opportunity_ids = store.out_ids("phx_dm_advisor_has_crm_opportunity", advisor_id)

    work: dict[tuple[str, str], dict] = {}
    pipeline: dict[str, dict] = {}

    def add_work(work_type: str, status: str, value: float) -> None:
        bucket = work.setdefault(
            (work_type, status),
            {"work_type": work_type, "status": status, "item_count": 0, "estimated_value": 0.0},
        )
        bucket["item_count"] += 1
        bucket["estimated_value"] += value

    for lead_id in lead_ids:
        attrs = store.vertex("phx_dm_crm_lead", lead_id) or {}
        add_work("LEAD", str(attrs.get("status")), float(attrs.get("estimated_value") or 0))
    for referral_id in referral_ids:
        attrs = store.vertex("phx_dm_crm_referral", referral_id) or {}
        add_work("REFERRAL", str(attrs.get("status")), float(attrs.get("estimated_value") or 0))
    for opportunity_id in opportunity_ids:
        attrs = store.vertex("phx_dm_crm_opportunity", opportunity_id) or {}
        amount = float(attrs.get("amount") or 0)
        probability = float(attrs.get("probability") or 0)
        add_work("CRM_OPPORTUNITY", str(attrs.get("status")), amount)
        stage = str(attrs.get("stage"))
        bucket = pipeline.setdefault(
            stage, {"stage": stage, "opportunity_count": 0, "pipeline_amount": 0.0, "weighted_amount": 0.0}
        )
        bucket["opportunity_count"] += 1
        bucket["pipeline_amount"] += amount
        bucket["weighted_amount"] += amount * probability

    return [
        {
            "advisor": vset(store, ADVISOR, [advisor_id]),
            "crm_work_summary": list(work.values()),
            "crm_pipeline": list(pipeline.values()),
            "leads": vset(store, "phx_dm_crm_lead", lead_ids),
            "referrals": vset(store, "phx_dm_crm_referral", referral_ids),
            "opportunities": vset(store, "phx_dm_crm_opportunity", opportunity_ids),
        }
    ]


@mock_query("get_agp_program_cohort_summary")
def get_agp_program_cohort_summary(store: FoundationGraphStore, params: dict) -> list[dict]:
    program_id = str(params.get("program_id") or "")
    cohort = str(params.get("cohort") or "ALL")
    scope_type = (params.get("scope_type") or "").upper()
    scope_id = str(params.get("scope_id") or "")

    advisor_ids = set(resolve_scope_advisor_ids(store, scope_type, scope_id))
    scoped_enrollments: list[str] = []
    for advisor_id in advisor_ids:
        for enrollment_id in store.out_ids("phx_dm_advisor_has_agp_enrollment", advisor_id):
            attrs = store.vertex("phx_dm_agp_enrollment", enrollment_id) or {}
            if program_id and program_id not in store.out_ids("phx_dm_enrollment_in_agp_program", enrollment_id):
                continue
            if cohort != "ALL" and str(attrs.get("cohort")) != cohort:
                continue
            scoped_enrollments.append(enrollment_id)

    progress_ids: list[str] = []
    milestone_summary: dict[str, dict] = {}
    for enrollment_id in scoped_enrollments:
        for progress_id in store.out_ids("phx_dm_enrollment_has_milestone_progress", enrollment_id):
            progress_ids.append(progress_id)
            attrs = store.vertex("phx_dm_agp_milestone_progress", progress_id) or {}
            status = str(attrs.get("status") or attrs.get("milestone_status"))
            bucket = milestone_summary.setdefault(
                status,
                {"milestone_status": status, "progress_count": 0, "attainment_sum": 0.0, "risk_sum": 0.0},
            )
            bucket["progress_count"] += 1
            bucket["attainment_sum"] += float(attrs.get("attainment_pct") or attrs.get("goal_attainment_pct") or 0)
            bucket["risk_sum"] += float(attrs.get("risk_score") or 0)

    return [
        {
            "program_id": program_id,
            "cohort": cohort,
            "scope_type": scope_type,
            "scope_id": scope_id,
            "enrollment_count": len(scoped_enrollments),
            "milestone_summary": list(milestone_summary.values()),
            "programs": vset(store, "phx_dm_agp_program", [program_id] if program_id else []),
            "scoped_enrollments": vset(store, "phx_dm_agp_enrollment", scoped_enrollments),
            "progress": vset(store, "phx_dm_agp_milestone_progress", progress_ids),
        }
    ]
