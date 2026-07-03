from __future__ import annotations

from app.graph.client import mock_query
from app.graph.foundation_store import FoundationGraphStore
from app.graph.queries.common import (
    ADVISOR,
    BRANCH,
    DIVISION,
    FIRM,
    MARKET,
    REGION,
    USER,
    resolve_scope_advisor_ids,
    vset,
)


@mock_query("get_org_hierarchy")
def get_org_hierarchy(store: FoundationGraphStore, params: dict) -> list[dict]:
    scope_type = (params.get("scope_type") or "").upper()
    scope_id = str(params.get("scope_id") or "")
    max_depth = int(params.get("max_depth") or 6)

    firms: list[str] = []
    divisions: list[str] = []
    regions: list[str] = []
    markets: list[str] = []
    branches: list[str] = []
    advisors: list[str] = []

    if scope_type == "FIRM":
        firms = [scope_id]
    elif scope_type == "DIVISION":
        divisions = [scope_id]
    elif scope_type == "REGION":
        regions = [scope_id]
    elif scope_type == "MARKET":
        markets = [scope_id]
    elif scope_type == "BRANCH":
        branches = [scope_id]
    elif scope_type == "ADVISOR":
        advisors = [scope_id]

    depth = 0
    for firm_id in list(firms):
        if max_depth >= 1:
            divisions.extend(store.in_ids("phx_dm_division_in_firm", firm_id))
        depth = 1
    for division_id in list(divisions):
        if max_depth >= depth + 1:
            regions.extend(store.in_ids("phx_dm_region_in_division", division_id))
    if divisions:
        depth += 1
    for region_id in list(regions):
        if max_depth >= depth + 1:
            markets.extend(store.in_ids("phx_dm_market_in_region", region_id))
    if regions:
        depth += 1
    for market_id in list(markets):
        if max_depth >= depth + 1:
            branches.extend(store.in_ids("phx_dm_branch_in_market", market_id))
            advisors.extend(store.in_ids("phx_dm_advisor_in_market", market_id))
    if markets:
        depth += 1
    for branch_id in list(branches):
        if max_depth >= depth + 1:
            advisors.extend(store.in_ids("phx_dm_advisor_in_branch", branch_id))

    return [
        {
            "firms": vset(store, FIRM, firms),
            "divisions": vset(store, DIVISION, divisions),
            "regions": vset(store, REGION, regions),
            "markets": vset(store, MARKET, markets),
            "branches": vset(store, BRANCH, branches),
            "advisors": vset(store, ADVISOR, advisors),
        }
    ]


@mock_query("get_scope_descendants")
def get_scope_descendants(store: FoundationGraphStore, params: dict) -> list[dict]:
    scope_type = (params.get("scope_type") or "").upper()
    scope_id = str(params.get("scope_id") or "")
    entity_type = (params.get("entity_type") or "ALL").upper()

    advisor_ids = resolve_scope_advisor_ids(store, scope_type, scope_id)
    household_ids: list[str] = []
    for advisor_id in advisor_ids:
        household_ids.extend(store.out_ids("phx_dm_advisor_serves_household", advisor_id))
    account_ids: list[str] = []
    for household_id in household_ids:
        account_ids.extend(store.out_ids("phx_dm_household_owns_account", household_id))

    return [
        {
            "scope_type": scope_type,
            "scope_id": scope_id,
            "entity_type": entity_type,
            "advisor_descendants": vset(store, ADVISOR, advisor_ids) if entity_type in {"ALL", "ADVISOR"} else [],
            "household_descendants": vset(store, "phx_dm_household", household_ids) if entity_type in {"ALL", "HOUSEHOLD"} else [],
            "account_descendants": vset(store, "phx_dm_account", account_ids) if entity_type in {"ALL", "ACCOUNT"} else [],
        }
    ]


@mock_query("get_management_chain")
def get_management_chain(store: FoundationGraphStore, params: dict) -> list[dict]:
    user_id = str(params.get("user_id") or "")
    advisor_id = str(params.get("advisor_id") or "")

    def users_with_role(ids: list[str], role: str) -> list[str]:
        return [uid for uid in ids if (store.vertex(USER, uid) or {}).get("role_code") == role]

    mdw_ids = users_with_role(store.in_ids("phx_dm_mdw_manages_advisor", advisor_id), "MDW")
    rdw_ids: list[str] = []
    for mdw_id in mdw_ids:
        rdw_ids.extend(users_with_role(store.in_ids("phx_dm_rdw_manages_mdw", mdw_id), "RDW"))
    ddw_ids: list[str] = []
    for rdw_id in rdw_ids:
        ddw_ids.extend(users_with_role(store.in_ids("phx_dm_ddw_manages_rdw", rdw_id), "DDW"))

    return [
        {
            "requester": vset(store, USER, [user_id]),
            "ddw": vset(store, USER, ddw_ids),
            "rdw": vset(store, USER, rdw_ids),
            "mdw": vset(store, USER, mdw_ids),
            "advisor": vset(store, ADVISOR, [advisor_id]),
        }
    ]


@mock_query("get_persona_scope_assignments")
def get_persona_scope_assignments(store: FoundationGraphStore, params: dict) -> list[dict]:
    user_id = str(params.get("user_id") or "")
    user_attrs = store.vertex(USER, user_id) or {}

    managed_rdws = [
        uid for uid in store.out_ids("phx_dm_ddw_manages_rdw", user_id)
        if (store.vertex(USER, uid) or {}).get("role_code") == "RDW"
    ]
    managed_mdws = [
        uid for uid in store.out_ids("phx_dm_rdw_manages_mdw", user_id)
        if (store.vertex(USER, uid) or {}).get("role_code") == "MDW"
    ]
    return [
        {
            "user": vset(store, USER, [user_id]),
            "firms": vset(store, FIRM, store.out_ids("phx_dm_user_scoped_to_firm", user_id)),
            "divisions": vset(store, DIVISION, store.out_ids("phx_dm_user_scoped_to_division", user_id)),
            "regions": vset(store, REGION, store.out_ids("phx_dm_user_scoped_to_region", user_id)),
            "markets": vset(store, MARKET, store.out_ids("phx_dm_user_scoped_to_market", user_id)),
            "branches": vset(store, BRANCH, store.out_ids("phx_dm_user_scoped_to_branch", user_id)),
            "advisors": vset(store, ADVISOR, store.out_ids("phx_dm_user_represents_advisor", user_id)),
            "managed_rdws": vset(store, USER, managed_rdws),
            "managed_mdws": vset(store, USER, managed_mdws),
            "managed_advisors": vset(store, ADVISOR, store.out_ids("phx_dm_mdw_manages_advisor", user_id)),
            "role_code": user_attrs.get("role_code"),
        }
    ]
