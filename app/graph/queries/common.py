from __future__ import annotations

from typing import Any, Iterable

from app.graph.foundation_store import FoundationGraphStore

# Vertex type constants (schema prefix phx_dm_)
FIRM = "phx_dm_firm"
DIVISION = "phx_dm_division"
REGION = "phx_dm_region"
MARKET = "phx_dm_market"
BRANCH = "phx_dm_branch"
ADVISOR = "phx_dm_advisor"
USER = "phx_dm_persona_user"
HOUSEHOLD = "phx_dm_household"
ACCOUNT = "phx_dm_account"
PRODUCT = "phx_dm_product"


def vertex_out(store: FoundationGraphStore, vertex_type: str, vertex_id: str) -> dict | None:
    """RESTPP-style vertex serialization: {"v_id", "v_type", "attributes"}."""
    attrs = store.vertex(vertex_type, vertex_id)
    if attrs is None:
        return None
    return {"v_id": str(vertex_id), "v_type": vertex_type, "attributes": attrs}


def vset(store: FoundationGraphStore, vertex_type: str, ids: Iterable[str]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for vid in ids:
        vid = str(vid)
        if vid in seen:
            continue
        seen.add(vid)
        v = vertex_out(store, vertex_type, vid)
        if v is not None:
            out.append(v)
    return out


def date10(value: Any) -> str:
    """Normalize a date/datetime string to its ISO date prefix for comparison."""
    return str(value or "")[:10]


def in_window(value: Any, start_date: Any, end_date: Any) -> bool:
    d = date10(value)
    return bool(d) and date10(start_date) <= d <= date10(end_date)


def resolve_scope_advisor_ids(store: FoundationGraphStore, scope_type: str, scope_id: str) -> list[str]:
    """Mirror of the GSQL scope-resolution block shared by GQ-004..007, 039, 041:
    FIRM -> divisions -> regions -> markets -> advisors (via advisor_in_market),
    BRANCH -> advisors via advisor_in_branch, ADVISOR -> itself, ALL -> everyone.
    """
    scope_type = (scope_type or "").upper()
    if scope_type == "ALL":
        return list(store.all_vertices(ADVISOR).keys())
    if scope_type == "ADVISOR":
        return [scope_id] if store.vertex(ADVISOR, scope_id) else []
    if scope_type == "BRANCH":
        return store.in_ids("phx_dm_advisor_in_branch", scope_id)
    if scope_type == "MARKET":
        return store.in_ids("phx_dm_advisor_in_market", scope_id)

    market_ids: list[str] = []
    if scope_type == "REGION":
        market_ids = store.in_ids("phx_dm_market_in_region", scope_id)
    elif scope_type == "DIVISION":
        for region_id in store.in_ids("phx_dm_region_in_division", scope_id):
            market_ids.extend(store.in_ids("phx_dm_market_in_region", region_id))
    elif scope_type == "FIRM":
        for division_id in store.in_ids("phx_dm_division_in_firm", scope_id):
            for region_id in store.in_ids("phx_dm_region_in_division", division_id):
                market_ids.extend(store.in_ids("phx_dm_market_in_region", region_id))
    advisor_ids: list[str] = []
    for market_id in market_ids:
        advisor_ids.extend(store.in_ids("phx_dm_advisor_in_market", market_id))
    return sorted(set(advisor_ids))


def advisor_transactions(
    store: FoundationGraphStore, advisor_ids: Iterable[str], start_date: Any = None, end_date: Any = None
) -> list[tuple[str, dict]]:
    """(transaction_id, attrs) for the advisors, optionally date-filtered
    (edge phx_dm_transaction_for_advisor points transaction -> advisor)."""
    rows: list[tuple[str, dict]] = []
    for advisor_id in advisor_ids:
        for tx_id in store.in_ids("phx_dm_transaction_for_advisor", advisor_id):
            attrs = store.vertex("phx_dm_revenue_transaction", tx_id)
            if attrs is None:
                continue
            if start_date is not None and not in_window(attrs.get("transaction_date"), start_date, end_date):
                continue
            rows.append((tx_id, attrs))
    return rows


def group_accum(rows: Iterable[dict], keys: list[str], sums: dict[str, str]) -> list[dict]:
    """GroupByAccum equivalent: group `rows` by `keys`, summing the mappings in
    `sums` (output_field -> input_field, input may be a literal 1 for counts)."""
    grouped: dict[tuple, dict] = {}
    for row in rows:
        key = tuple(row.get(k) for k in keys)
        bucket = grouped.setdefault(key, {**{k: row.get(k) for k in keys}, **{f: 0 for f in sums}})
        for out_field, in_field in sums.items():
            value = 1 if in_field == "__count__" else float(row.get(in_field) or 0)
            bucket[out_field] += value
    return list(grouped.values())
