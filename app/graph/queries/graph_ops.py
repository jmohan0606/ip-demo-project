from __future__ import annotations

from app.graph.client import mock_query
from app.graph.foundation_store import FoundationGraphStore
from app.graph.queries.common import ACCOUNT, ADVISOR, HOUSEHOLD, PRODUCT, vset


@mock_query("get_graph_subgraph")
def get_graph_subgraph(store: FoundationGraphStore, params: dict) -> list[dict]:
    root_type = (params.get("root_type") or "").upper()
    root_id = str(params.get("root_id") or "")
    max_depth = int(params.get("max_depth") or 2)
    node_limit = int(params.get("node_limit") or 100)

    advisors: list[str] = []
    households: list[str] = []
    accounts: list[str] = []
    products: list[str] = []

    if root_type == "ADVISOR":
        advisors = [root_id]
        if max_depth >= 1:
            households = store.out_ids("phx_dm_advisor_serves_household", root_id)[:node_limit]
        if max_depth >= 2:
            for household_id in households:
                accounts.extend(store.out_ids("phx_dm_household_owns_account", household_id))
            accounts = accounts[:node_limit]
        if max_depth >= 3:
            for account_id in accounts:
                products.extend(store.out_ids("phx_dm_account_holds_product", account_id))
            products = products[:node_limit]
    elif root_type == "HOUSEHOLD":
        households = [root_id]
        if max_depth >= 1:
            advisors = store.in_ids("phx_dm_advisor_serves_household", root_id)[:node_limit]
            accounts = store.out_ids("phx_dm_household_owns_account", root_id)[:node_limit]
        if max_depth >= 2:
            for account_id in accounts:
                products.extend(store.out_ids("phx_dm_account_holds_product", account_id))
            products = products[:node_limit]
    elif root_type == "ACCOUNT":
        accounts = [root_id]
        if max_depth >= 1:
            households = store.in_ids("phx_dm_household_owns_account", root_id)[:node_limit]
            products = store.out_ids("phx_dm_account_holds_product", root_id)[:node_limit]
        if max_depth >= 2:
            for household_id in households:
                advisors.extend(store.in_ids("phx_dm_advisor_serves_household", household_id))
            advisors = advisors[:node_limit]
    elif root_type == "PRODUCT":
        products = [root_id]
        if max_depth >= 1:
            accounts = store.in_ids("phx_dm_account_holds_product", root_id)[:node_limit]
        if max_depth >= 2:
            for account_id in accounts:
                households.extend(store.in_ids("phx_dm_household_owns_account", account_id))
            households = households[:node_limit]

    return [
        {
            "root_type": root_type,
            "root_id": root_id,
            "max_depth": max_depth,
            "advisors": vset(store, ADVISOR, advisors),
            "households": vset(store, HOUSEHOLD, households),
            "accounts": vset(store, ACCOUNT, accounts),
            "products": vset(store, PRODUCT, products),
        }
    ]


@mock_query("get_data_health_summary")
def get_data_health_summary(store: FoundationGraphStore, params: dict) -> list[dict]:
    stats = store.statistics()
    vertex_counts = [
        {"vertex_type": vertex_type, "vertex_count": count}
        for vertex_type, count in sorted(stats["vertex_counts"].items())
    ]
    edge_traversals = [
        {"edge_type": edge_type, "traversal_count": count}
        for edge_type, count in sorted(stats["edge_counts"].items())
    ]
    return [{"vertex_counts": vertex_counts, "connected_edge_traversals": edge_traversals}]


@mock_query("get_what_if_baseline")
def get_what_if_baseline(store: FoundationGraphStore, params: dict) -> list[dict]:
    scenario_type = (params.get("scenario_type") or "").upper()
    scope_type = (params.get("scope_type") or "").upper()
    scope_id = str(params.get("scope_id") or "")

    scenario_ids = [
        sid
        for sid, attrs in store.all_vertices("phx_dm_simulation_scenario").items()
        if str(attrs.get("scenario_type", "")).upper() == scenario_type
    ]
    advisor_ids = [scope_id] if scope_type == "ADVISOR" and store.vertex(ADVISOR, scope_id) else []
    features: list[str] = []
    predictions: list[str] = []
    opportunities: list[str] = []
    for advisor_id in advisor_ids:
        features.extend(store.out_ids("phx_dm_advisor_has_feature_snapshot", advisor_id))
        predictions.extend(store.in_ids("phx_dm_prediction_for_advisor", advisor_id))
        opportunities.extend(store.in_ids("phx_dm_opportunity_for_advisor", advisor_id))
    return [
        {
            "scenario_type": scenario_type,
            "scope_type": scope_type,
            "scope_id": scope_id,
            "scenarios": vset(store, "phx_dm_simulation_scenario", scenario_ids),
            "advisors": vset(store, ADVISOR, advisor_ids),
            "features": vset(store, "phx_dm_feature_snapshot", features),
            "predictions": vset(store, "phx_dm_prediction_result", predictions),
            "opportunities": vset(store, "phx_dm_opportunity", opportunities),
        }
    ]


@mock_query("get_data_quality_issues")
def get_data_quality_issues(store: FoundationGraphStore, params: dict) -> list[dict]:
    domain = (params.get("domain") or "ALL").upper()
    severity = (params.get("severity") or "ALL").upper()
    limit = int(params.get("result_limit") or 100)

    issues_by_severity: dict[str, int] = {}
    issue_count = 0

    def record(sev: str, count: int) -> None:
        nonlocal issue_count
        issue_count += count
        issues_by_severity[sev] = issues_by_severity.get(sev, 0) + count

    advisors_missing_branch = []
    if domain in {"ALL", "ORGANIZATION"}:
        advisors_missing_branch = [
            aid for aid in store.all_vertices(ADVISOR) if not store.out_ids("phx_dm_advisor_in_branch", aid)
        ][:limit]
        record("HIGH", len(advisors_missing_branch))

    households_missing_advisor = []
    if domain in {"ALL", "HOUSEHOLD"}:
        households_missing_advisor = [
            hid for hid in store.all_vertices(HOUSEHOLD) if not store.in_ids("phx_dm_advisor_serves_household", hid)
        ][:limit]
        record("HIGH", len(households_missing_advisor))

    accounts_missing_household = []
    if domain in {"ALL", "ACCOUNT"}:
        accounts_missing_household = [
            aid for aid in store.all_vertices(ACCOUNT) if not store.in_ids("phx_dm_household_owns_account", aid)
        ][:limit]
        record("MEDIUM", len(accounts_missing_household))

    predictions_missing_features = []
    if domain in {"ALL", "AI"}:
        predictions_missing_features = [
            pid
            for pid in store.all_vertices("phx_dm_prediction_result")
            if not store.out_ids("phx_dm_prediction_uses_feature_snapshot", pid)
        ][:limit]
        record("MEDIUM", len(predictions_missing_features))

    recommendations_missing_reasoning = []
    if domain in {"ALL", "AI"}:
        recommendations_missing_reasoning = [
            rid
            for rid in store.all_vertices("phx_dm_recommendation")
            if not store.in_ids("phx_dm_reasoning_for_recommendation", rid)
        ][:limit]
        record("MEDIUM", len(recommendations_missing_reasoning))

    severity_rows = [
        {"issue_severity": sev, "issue_count": count}
        for sev, count in issues_by_severity.items()
        if severity == "ALL" or sev == severity
    ]
    return [
        {
            "domain": domain,
            "severity": severity,
            "issue_count": issue_count,
            "issues_by_severity": severity_rows,
            "advisors_missing_branch": vset(store, ADVISOR, advisors_missing_branch),
            "households_missing_advisor": vset(store, HOUSEHOLD, households_missing_advisor),
            "accounts_missing_household": vset(store, ACCOUNT, accounts_missing_household),
            "predictions_missing_features": vset(store, "phx_dm_prediction_result", predictions_missing_features),
            "recommendations_missing_reasoning": vset(store, "phx_dm_recommendation", recommendations_missing_reasoning),
        }
    ]


@mock_query("get_documents")
def get_documents(store: FoundationGraphStore, params: dict) -> list[dict]:
    """GQ-058 mock — bounded phx_dm_document listing ordered by document_id."""
    result_limit = int(params.get("result_limit") or 1000)
    doc_ids = sorted(store.all_vertices("phx_dm_document").keys())[:result_limit]
    return [{"documents": vset(store, "phx_dm_document", doc_ids)}]
