from __future__ import annotations

from fastapi import APIRouter

from app.graph.client import get_graph_client
from app.graph.queries.common import resolve_scope_advisor_ids
from app.shared.responses import ok

router = APIRouter(prefix="/hierarchy", tags=["Hierarchy"])

# child -> parent edges of the org hierarchy (traverse with in_ids to get children).
_FIRM = "phx_dm_firm"
_DIVISION = "phx_dm_division"
_REGION = "phx_dm_region"
_MARKET = "phx_dm_market"
_ADVISOR = "phx_dm_advisor"


def _name(store, vtype: str, vid: str, name_attr: str) -> str:
    attrs = store.vertex(vtype, vid) or {}
    return str(attrs.get(name_attr) or vid)


@router.get("/tree")
def tree():
    """Real org tree from the graph: Firm > Divisions > Regions > Markets > Advisors.
    Drives the hierarchy breadcrumb; every node carries scope_type + scope_id so a
    selection re-scopes page data."""
    store = get_graph_client().store
    firms = []
    for firm_id in store.all_vertices(_FIRM):
        divisions = []
        for div_id in store.in_ids("phx_dm_division_in_firm", firm_id):
            regions = []
            for reg_id in store.in_ids("phx_dm_region_in_division", div_id):
                markets = []
                for mkt_id in store.in_ids("phx_dm_market_in_region", reg_id):
                    advisors = [
                        {"scope_type": "Advisor", "scope_id": adv_id,
                         "label": _name(store, _ADVISOR, adv_id, "advisor_name")}
                        for adv_id in sorted(store.in_ids("phx_dm_advisor_in_market", mkt_id))
                    ]
                    markets.append({
                        "scope_type": "Market", "scope_id": mkt_id,
                        "label": _name(store, _MARKET, mkt_id, "market_name"),
                        "children": advisors,
                    })
                regions.append({
                    "scope_type": "Region", "scope_id": reg_id,
                    "label": _name(store, _REGION, reg_id, "region_name"),
                    "children": sorted(markets, key=lambda m: m["scope_id"]),
                })
            divisions.append({
                "scope_type": "Division", "scope_id": div_id,
                "label": _name(store, _DIVISION, div_id, "division_name"),
                "children": sorted(regions, key=lambda r: r["scope_id"]),
            })
        firms.append({
            "scope_type": "Firm", "scope_id": firm_id,
            "label": _name(store, _FIRM, firm_id, "firm_name"),
            "children": sorted(divisions, key=lambda d: d["scope_id"]),
        })
    return ok(data={"firms": firms})


@router.get("/entity-names")
def entity_names():
    """Flat {entity_id: real_name} map across every entity type — the single source the
    frontend's shared entity-label helper uses to render "ID · Name" everywhere (item 3)."""
    store = get_graph_client().store
    names: dict[str, str] = {}
    for vtype, attr in (
        (_FIRM, "firm_name"), (_DIVISION, "division_name"), (_REGION, "region_name"),
        (_MARKET, "market_name"), ("phx_dm_branch", "branch_name"),
        (_ADVISOR, "advisor_name"), ("phx_dm_household", "household_name"),
    ):
        for vid, attrs in store.all_vertices(vtype).items():
            nm = attrs.get(attr)
            if nm:
                names[str(vid)] = str(nm)
    return ok(data={"names": names, "count": len(names)})


@router.get("/resolve")
def resolve(scope_type: str = "ALL", scope_id: str = ""):
    """Advisor ids under a scope — the aggregation primitive for scope-aware rollups."""
    store = get_graph_client().store
    advisor_ids = resolve_scope_advisor_ids(store, scope_type, scope_id)
    return ok(data={
        "scope_type": scope_type,
        "scope_id": scope_id,
        "advisor_count": len(advisor_ids),
        "advisor_ids": advisor_ids,
    })
