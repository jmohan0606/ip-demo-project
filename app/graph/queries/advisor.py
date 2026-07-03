from __future__ import annotations

from app.graph.client import mock_query
from app.graph.foundation_store import FoundationGraphStore
from app.graph.queries.common import ADVISOR, HOUSEHOLD, ACCOUNT, vset


@mock_query("get_advisor_360")
def get_advisor_360(store: FoundationGraphStore, params: dict) -> list[dict]:
    advisor_id = str(params.get("advisor_id") or "")
    household_ids = store.out_ids("phx_dm_advisor_serves_household", advisor_id)
    account_ids: list[str] = []
    for household_id in household_ids:
        account_ids.extend(store.out_ids("phx_dm_household_owns_account", household_id))
    return [
        {
            "advisor": vset(store, ADVISOR, [advisor_id]),
            "branch": vset(store, "phx_dm_branch", store.out_ids("phx_dm_advisor_in_branch", advisor_id)),
            "market": vset(store, "phx_dm_market", store.out_ids("phx_dm_advisor_in_market", advisor_id)),
            "households": vset(store, HOUSEHOLD, household_ids),
            "accounts": vset(store, ACCOUNT, account_ids),
            "crm_activities": vset(store, "phx_dm_crm_activity", store.in_ids("phx_dm_activity_for_advisor", advisor_id)),
            "crm_leads": vset(store, "phx_dm_crm_lead", store.out_ids("phx_dm_advisor_has_crm_lead", advisor_id)),
            "crm_referrals": vset(store, "phx_dm_crm_referral", store.out_ids("phx_dm_advisor_has_crm_referral", advisor_id)),
            "crm_opportunities": vset(store, "phx_dm_crm_opportunity", store.out_ids("phx_dm_advisor_has_crm_opportunity", advisor_id)),
            "enrollments": vset(store, "phx_dm_agp_enrollment", store.out_ids("phx_dm_advisor_has_agp_enrollment", advisor_id)),
            "predictions": vset(store, "phx_dm_prediction_result", store.in_ids("phx_dm_prediction_for_advisor", advisor_id)),
            "opportunities": vset(store, "phx_dm_opportunity", store.in_ids("phx_dm_opportunity_for_advisor", advisor_id)),
            "recommendations": vset(store, "phx_dm_recommendation", store.in_ids("phx_dm_recommendation_for_advisor", advisor_id)),
            "memories": vset(store, "phx_dm_context_memory", store.in_ids("phx_dm_memory_for_advisor", advisor_id)),
            "features": vset(store, "phx_dm_feature_snapshot", store.out_ids("phx_dm_advisor_has_feature_snapshot", advisor_id)),
            "embeddings": vset(store, "phx_dm_embedding", store.out_ids("phx_dm_advisor_has_embedding", advisor_id)),
        }
    ]


@mock_query("get_advisor_book_of_business")
def get_advisor_book_of_business(store: FoundationGraphStore, params: dict) -> list[dict]:
    advisor_id = str(params.get("advisor_id") or "")
    result_limit = int(params.get("result_limit") or 20)
    household_ids = store.out_ids("phx_dm_advisor_serves_household", advisor_id)[:result_limit]
    account_ids: list[str] = []
    summary: list[dict] = []
    for household_id in household_ids:
        account_ids.extend(store.out_ids("phx_dm_household_owns_account", household_id))
        household = store.vertex("phx_dm_household", household_id) or {}
        revenue = 0.0
        count = 0
        for tx_id in store.in_ids("phx_dm_transaction_for_household", household_id):
            attrs = store.vertex("phx_dm_revenue_transaction", tx_id) or {}
            revenue += float(attrs.get("revenue_amount") or 0)
            count += 1
        summary.append(
            {
                "household_id": household_id,
                "household_name": household.get("household_name"),
                "revenue": round(revenue, 2),
                "transaction_count": count,
            }
        )
    summary.sort(key=lambda r: -r["revenue"])
    return [
        {
            "advisor": vset(store, ADVISOR, [advisor_id]),
            "households": vset(store, HOUSEHOLD, household_ids),
            "accounts": vset(store, ACCOUNT, account_ids),
            "household_revenue_summary": summary,
        }
    ]


@mock_query("get_household_360")
def get_household_360(store: FoundationGraphStore, params: dict) -> list[dict]:
    household_id = str(params.get("household_id") or "")
    return [
        {
            "household": vset(store, HOUSEHOLD, [household_id]),
            "advisors": vset(store, ADVISOR, store.in_ids("phx_dm_advisor_serves_household", household_id)),
            "accounts": vset(store, ACCOUNT, store.out_ids("phx_dm_household_owns_account", household_id)),
            "activities": vset(store, "phx_dm_crm_activity", store.in_ids("phx_dm_activity_for_household", household_id)),
            "leads": vset(store, "phx_dm_crm_lead", store.in_ids("phx_dm_lead_for_household", household_id)),
            "referrals": vset(store, "phx_dm_crm_referral", store.in_ids("phx_dm_referral_for_household", household_id)),
            "crm_opportunities": vset(store, "phx_dm_crm_opportunity", store.in_ids("phx_dm_crm_opportunity_for_household", household_id)),
            "predictions": vset(store, "phx_dm_prediction_result", store.in_ids("phx_dm_prediction_for_household", household_id)),
            "opportunities": vset(store, "phx_dm_opportunity", store.in_ids("phx_dm_opportunity_for_household", household_id)),
            "recommendations": vset(store, "phx_dm_recommendation", store.in_ids("phx_dm_recommendation_for_household", household_id)),
            "memories": vset(store, "phx_dm_context_memory", store.in_ids("phx_dm_memory_for_household", household_id)),
            "features": vset(store, "phx_dm_feature_snapshot", store.out_ids("phx_dm_household_has_feature_snapshot", household_id)),
            "embeddings": vset(store, "phx_dm_embedding", store.out_ids("phx_dm_household_has_embedding", household_id)),
        }
    ]


@mock_query("get_account_holdings_and_activity")
def get_account_holdings_and_activity(store: FoundationGraphStore, params: dict) -> list[dict]:
    account_id = str(params.get("account_id") or "")
    return [
        {
            "account": vset(store, ACCOUNT, [account_id]),
            "households": vset(store, HOUSEHOLD, store.in_ids("phx_dm_household_owns_account", account_id)),
            "products": vset(store, "phx_dm_product", store.out_ids("phx_dm_account_holds_product", account_id)),
            "activities": vset(store, "phx_dm_crm_activity", store.in_ids("phx_dm_activity_for_account", account_id)),
            "transactions": vset(store, "phx_dm_revenue_transaction", store.in_ids("phx_dm_transaction_for_account", account_id)),
            "crm_opportunities": vset(store, "phx_dm_crm_opportunity", store.in_ids("phx_dm_crm_opportunity_for_account", account_id)),
            "predictions": vset(store, "phx_dm_prediction_result", store.in_ids("phx_dm_prediction_for_account", account_id)),
            "opportunities": vset(store, "phx_dm_opportunity", store.in_ids("phx_dm_opportunity_for_account", account_id)),
            "recommendations": vset(store, "phx_dm_recommendation", store.in_ids("phx_dm_recommendation_for_account", account_id)),
            "features": vset(store, "phx_dm_feature_snapshot", store.out_ids("phx_dm_account_has_feature_snapshot", account_id)),
            "embeddings": vset(store, "phx_dm_embedding", store.out_ids("phx_dm_account_has_embedding", account_id)),
        }
    ]
