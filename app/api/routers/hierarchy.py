from __future__ import annotations

import logging

from fastapi import APIRouter

from app.graph.client import get_graph_client
from app.graph.queries.common import (
    graph_fallback_store,
    resolve_scope_advisor_ids_graph,
    run_catalog_query,
    scope_advisor_placements,
)
from app.shared.responses import ok

logger = logging.getLogger(__name__)

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


def _tree_from_placements(placements: dict[str, dict]) -> list[dict]:
    """Rebuild the nested Firm > Division > Region > Market > Advisor tree from the
    flat per-advisor ancestor placements returned by GQ-053 (ids + display names)."""
    firms: dict[str, dict] = {}
    for advisor_id, attrs in placements.items():
        firm_id = str(attrs.get("firm_id") or "")
        div_id = str(attrs.get("division_id") or "")
        reg_id = str(attrs.get("region_id") or "")
        mkt_id = str(attrs.get("market_id") or "")
        if not (firm_id and div_id and reg_id and mkt_id):
            continue  # advisor with an incomplete ancestor chain cannot be placed
        firm = firms.setdefault(
            firm_id, {"label": str(attrs.get("firm_name") or firm_id), "divisions": {}}
        )
        division = firm["divisions"].setdefault(
            div_id, {"label": str(attrs.get("division_name") or div_id), "regions": {}}
        )
        region = division["regions"].setdefault(
            reg_id, {"label": str(attrs.get("region_name") or reg_id), "markets": {}}
        )
        market = region["markets"].setdefault(
            mkt_id, {"label": str(attrs.get("market_name") or mkt_id), "advisors": {}}
        )
        market["advisors"][str(advisor_id)] = str(attrs.get("advisor_name") or advisor_id)

    out: list[dict] = []
    for firm_id, firm in sorted(firms.items()):
        divisions = []
        for div_id, division in sorted(firm["divisions"].items()):
            regions = []
            for reg_id, region in sorted(division["regions"].items()):
                markets = []
                for mkt_id, market in sorted(region["markets"].items()):
                    advisors = [
                        {"scope_type": "Advisor", "scope_id": adv_id, "label": label}
                        for adv_id, label in sorted(market["advisors"].items())
                    ]
                    markets.append({
                        "scope_type": "Market", "scope_id": mkt_id,
                        "label": market["label"],
                        "children": advisors,
                    })
                regions.append({
                    "scope_type": "Region", "scope_id": reg_id,
                    "label": region["label"],
                    "children": markets,
                })
            divisions.append({
                "scope_type": "Division", "scope_id": div_id,
                "label": division["label"],
                "children": regions,
            })
        out.append({
            "scope_type": "Firm", "scope_id": firm_id,
            "label": firm["label"],
            "children": divisions,
        })
    return out


def _tree_from_store(store) -> list[dict]:
    """Logged local-store fallback: the original direct traversal, unchanged."""
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
    return firms


@router.get("/tree")
def tree():
    """Real org tree from the graph: Firm > Divisions > Regions > Markets > Advisors.
    Drives the hierarchy breadcrumb; every node carries scope_type + scope_id so a
    selection re-scopes page data."""
    graph = get_graph_client()
    placements = scope_advisor_placements(graph, "ALL", "")
    if placements is not None:
        return ok(data={"firms": _tree_from_placements(placements)})
    logger.warning(
        "hierarchy /tree: get_scope_advisor_placements (GQ-053) unavailable — "
        "falling back to local store traversal"
    )
    return ok(data={"firms": _tree_from_store(graph_fallback_store(graph))})


def _entity_names_from_store(store) -> dict[str, str]:
    """Logged local-store fallback: the original direct traversal, unchanged."""
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
    return names


@router.get("/entity-names")
def entity_names():
    """Flat {entity_id: real_name} map across every entity type — the single source the
    frontend's shared entity-label helper uses to render "ID · Name" everywhere (item 3)."""
    graph = get_graph_client()
    names = _entity_names_from_queries(graph)
    if names is None:
        logger.warning(
            "hierarchy /entity-names: catalogued queries (GQ-053/GQ-002) unavailable — "
            "falling back to local store traversal"
        )
        names = _entity_names_from_store(graph_fallback_store(graph))
    return ok(data={"names": names, "count": len(names)})


def _entity_names_from_queries(graph) -> dict[str, str] | None:
    """Entity-id -> display-name map via GQ-053 (firm/division/region/market/branch/
    advisor names from each advisor's ancestor placement) + GQ-002 (household names).
    Returns None when either query is unavailable — caller uses the logged fallback."""
    placements = scope_advisor_placements(graph, "ALL", "")
    if placements is None:
        return None
    households = run_catalog_query(
        graph,
        "get_scope_descendants",
        {"scope_type": "ALL", "scope_id": "", "entity_type": "HOUSEHOLD"},
    )
    if households is None:
        return None
    household_rows = None
    for entry in households:
        if entry.get("household_descendants") is not None:
            household_rows = entry["household_descendants"]
            break
    if household_rows is None:
        logger.warning(
            "hierarchy /entity-names: get_scope_descendants returned no "
            "household_descendants entry"
        )
        return None

    names: dict[str, str] = {}
    for advisor_id, attrs in placements.items():
        for id_key, name_key in (
            ("firm_id", "firm_name"), ("division_id", "division_name"),
            ("region_id", "region_name"), ("market_id", "market_name"),
            ("branch_id", "branch_name"),
        ):
            eid, nm = attrs.get(id_key), attrs.get(name_key)
            if eid and nm:
                names[str(eid)] = str(nm)
        advisor_name = attrs.get("advisor_name")
        if advisor_name:
            names[str(advisor_id)] = str(advisor_name)
    for row in household_rows:
        row_attrs = row.get("attributes", row)
        nm = row_attrs.get("household_name")
        if nm and row.get("v_id") is not None:
            names[str(row["v_id"])] = str(nm)
    return names


@router.get("/resolve")
def resolve(scope_type: str = "ALL", scope_id: str = ""):
    """Advisor ids under a scope — the aggregation primitive for scope-aware rollups."""
    advisor_ids = resolve_scope_advisor_ids_graph(get_graph_client(), scope_type, scope_id)
    return ok(data={
        "scope_type": scope_type,
        "scope_id": scope_id,
        "advisor_count": len(advisor_ids),
        "advisor_ids": advisor_ids,
    })
