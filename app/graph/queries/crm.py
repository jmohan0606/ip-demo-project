from __future__ import annotations

from app.graph.client import mock_query
from app.graph.foundation_store import FoundationGraphStore
from app.graph.queries.common import ADVISOR, vset


def _status_filter(store: FoundationGraphStore, vertex_type: str, ids: list[str], status: str, limit: int) -> list[str]:
    status = (status or "ALL").upper()
    kept = []
    for vid in ids:
        attrs = store.vertex(vertex_type, vid) or {}
        if status == "ALL" or str(attrs.get("status", "")).upper() == status:
            kept.append(vid)
        if len(kept) >= limit:
            break
    return kept


@mock_query("get_crm_leads")
def get_crm_leads(store: FoundationGraphStore, params: dict) -> list[dict]:
    advisor_id = str(params.get("advisor_id") or "")
    status = params.get("status") or "ALL"
    limit = int(params.get("result_limit") or 20)
    lead_ids = _status_filter(
        store, "phx_dm_crm_lead", store.out_ids("phx_dm_advisor_has_crm_lead", advisor_id), status, limit
    )
    household_ids: list[str] = []
    opportunity_ids: list[str] = []
    for lead_id in lead_ids:
        household_ids.extend(store.out_ids("phx_dm_lead_for_household", lead_id))
        opportunity_ids.extend(store.out_ids("phx_dm_lead_generates_crm_opportunity", lead_id))
    return [
        {
            "advisor": vset(store, ADVISOR, [advisor_id]),
            "leads": vset(store, "phx_dm_crm_lead", lead_ids),
            "households": vset(store, "phx_dm_household", household_ids),
            "opportunities": vset(store, "phx_dm_crm_opportunity", opportunity_ids),
        }
    ]


@mock_query("get_crm_referrals")
def get_crm_referrals(store: FoundationGraphStore, params: dict) -> list[dict]:
    advisor_id = str(params.get("advisor_id") or "")
    status = params.get("status") or "ALL"
    limit = int(params.get("result_limit") or 20)
    referral_ids = _status_filter(
        store, "phx_dm_crm_referral", store.out_ids("phx_dm_advisor_has_crm_referral", advisor_id), status, limit
    )
    household_ids: list[str] = []
    opportunity_ids: list[str] = []
    for referral_id in referral_ids:
        household_ids.extend(store.out_ids("phx_dm_referral_for_household", referral_id))
        opportunity_ids.extend(store.out_ids("phx_dm_referral_generates_crm_opportunity", referral_id))
    return [
        {
            "advisor": vset(store, ADVISOR, [advisor_id]),
            "referrals": vset(store, "phx_dm_crm_referral", referral_ids),
            "households": vset(store, "phx_dm_household", household_ids),
            "opportunities": vset(store, "phx_dm_crm_opportunity", opportunity_ids),
        }
    ]


@mock_query("get_crm_opportunities")
def get_crm_opportunities(store: FoundationGraphStore, params: dict) -> list[dict]:
    advisor_id = str(params.get("advisor_id") or "")
    status = params.get("status") or "ALL"
    limit = int(params.get("result_limit") or 20)
    opportunity_ids = _status_filter(
        store,
        "phx_dm_crm_opportunity",
        store.out_ids("phx_dm_advisor_has_crm_opportunity", advisor_id),
        status,
        limit,
    )
    household_ids: list[str] = []
    account_ids: list[str] = []
    product_ids: list[str] = []
    for opportunity_id in opportunity_ids:
        household_ids.extend(store.out_ids("phx_dm_crm_opportunity_for_household", opportunity_id))
        account_ids.extend(store.out_ids("phx_dm_crm_opportunity_for_account", opportunity_id))
        product_ids.extend(store.out_ids("phx_dm_crm_opportunity_for_product", opportunity_id))
    return [
        {
            "advisor": vset(store, ADVISOR, [advisor_id]),
            "opportunities": vset(store, "phx_dm_crm_opportunity", opportunity_ids),
            "households": vset(store, "phx_dm_household", household_ids),
            "accounts": vset(store, "phx_dm_account", account_ids),
            "products": vset(store, "phx_dm_product", product_ids),
        }
    ]


@mock_query("get_crm_pipeline_by_stage")
def get_crm_pipeline_by_stage(store: FoundationGraphStore, params: dict) -> list[dict]:
    advisor_id = str(params.get("advisor_id") or "")
    opportunity_ids = store.out_ids("phx_dm_advisor_has_crm_opportunity", advisor_id)
    pipeline: dict[str, dict] = {}
    for opportunity_id in opportunity_ids:
        attrs = store.vertex("phx_dm_crm_opportunity", opportunity_id) or {}
        amount = float(attrs.get("amount") or 0)
        probability = float(attrs.get("probability") or 0)
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
            "pipeline_by_stage": list(pipeline.values()),
            "opportunities": vset(store, "phx_dm_crm_opportunity", opportunity_ids),
        }
    ]
