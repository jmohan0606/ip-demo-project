from __future__ import annotations

"""Section 11.8 — MCP layer completion.

Section 9.4's 4-tier GraphClient already covers graph ACCESS. Per the MCP poster, the agent
layer's tool registry should also expose FEATURE-STORE lookups and MODEL-SERVING (predict for
advisor X) as MCP tools. This registry defines those two tool families in the MCP tool shape
(name, description, JSON input schema, handler) alongside the existing graph family, so the
agent tool registry matches the poster. Bounded: registry + the two families, not an exhaustive
catalog.
"""

from typing import Any, Callable

from app.shared.responses import ok  # noqa: F401 — kept for callers that wrap results


def _predict_risk(advisor_id: str) -> dict:
    from app.prediction.service import PredictionService
    return PredictionService().predict_advisor(advisor_id, persist=False)


def _forecast_revenue(advisor_id: str, horizon: int = 6) -> dict:
    from app.ml.client import get_model_client
    from app.ml.training.datasets import monthly_revenue_series
    labels, series = monthly_revenue_series()
    history = [{"month": m, "value": v} for m, v in zip(labels, series.get(advisor_id, []))]
    return get_model_client().forecast_series("ADVISOR", advisor_id, history, horizon)


def _similar_advisors(advisor_id: str, top_k: int = 5) -> dict:
    from app.ml import registry
    from app.ml.vector_client import get_vector_client
    vc = get_vector_client()
    vec = vc.get("ADVISOR", advisor_id)
    if vec is None:
        return {"available": False, "advisor_id": advisor_id}
    return {"available": True, "advisor_id": advisor_id, "model": registry.active_embedding_model(),
            "matches": vc.search("ADVISOR", vec, top_k, exclude_id=advisor_id)}


def _household_churn(advisor_id: str) -> dict:
    from app.ml.client import get_model_client
    return get_model_client().household_churn(advisor_id)


def _feature_snapshot(advisor_id: str) -> dict:
    from app.features.engineering import FeatureEngineeringService
    from app.features.snapshot_store import SnapshotStore
    snap = SnapshotStore().latest_for_entity("ADVISOR", advisor_id)
    if not snap:
        snap = FeatureEngineeringService().compute_advisor_snapshot(advisor_id)
        return {"snapshot_id": snap.snapshot_id, "features": snap.values(), "lineage": snap.lineage()}
    return snap


def _list_features(advisor_id: str) -> dict:
    snap = _feature_snapshot(advisor_id)
    feats = snap.get("features", {})
    return {"advisor_id": advisor_id, "feature_count": len(feats), "features": feats}


_STR_ADVISOR = {"type": "object", "properties": {"advisor_id": {"type": "string"}}, "required": ["advisor_id"]}

# The MCP tool catalog: family -> [tool descriptors].
_TOOLS: dict[str, dict[str, Any]] = {
    # --- feature-store family ---
    "feature_store.get_snapshot": {
        "family": "feature_store", "description": "Latest computed feature snapshot for an advisor (33 Feature_Catalog features + lineage).",
        "input_schema": _STR_ADVISOR, "handler": _feature_snapshot},
    "feature_store.list_features": {
        "family": "feature_store", "description": "Flat feature name→value map for an advisor.",
        "input_schema": _STR_ADVISOR, "handler": _list_features},
    # --- model-serving family ---
    "model.predict_risk": {
        "family": "model_serving", "description": "Serve risk predictions (revenue-decline + AGP off-track) for an advisor, with contributions.",
        "input_schema": _STR_ADVISOR, "handler": _predict_risk},
    "model.forecast_revenue": {
        "family": "model_serving", "description": "6-month revenue forecast (GRU or seasonal-naive) with uncertainty band.",
        "input_schema": {"type": "object", "properties": {"advisor_id": {"type": "string"}, "horizon": {"type": "integer", "default": 6}}, "required": ["advisor_id"]},
        "handler": _forecast_revenue},
    "model.similar_advisors": {
        "family": "model_serving", "description": "Nearest advisors by GNN embedding similarity.",
        "input_schema": {"type": "object", "properties": {"advisor_id": {"type": "string"}, "top_k": {"type": "integer", "default": 5}}, "required": ["advisor_id"]},
        "handler": _similar_advisors},
    "model.household_churn": {
        "family": "model_serving", "description": "Per-household churn propensity for an advisor's book (indicative until gated).",
        "input_schema": _STR_ADVISOR, "handler": _household_churn},
}


def catalog() -> dict:
    """MCP tool catalog (poster shape): families + tool descriptors (no handlers)."""
    tools = [{"name": name, "family": t["family"], "description": t["description"], "input_schema": t["input_schema"]}
             for name, t in _TOOLS.items()]
    families: dict[str, list[str]] = {}
    for t in tools:
        families.setdefault(t["family"], []).append(t["name"])
    return {"families": families, "tool_count": len(tools), "tools": tools,
            "note": "Graph access is served by the Section-9.4 4-tier GraphClient MCP adapter; "
                    "these two families (feature_store, model_serving) complete the MCP tool registry."}


def invoke(tool_name: str, arguments: dict[str, Any]) -> dict:
    tool = _TOOLS.get(tool_name)
    if not tool:
        raise KeyError(f"unknown MCP tool '{tool_name}'")
    handler: Callable = tool["handler"]
    return handler(**(arguments or {}))
