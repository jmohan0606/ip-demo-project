from __future__ import annotations

import json
import math

from app.graph.client import get_graph_client

# Extends the existing advisor similarity capability to other entity types
# (household, account, portfolio) by computing cosine nearest-neighbours directly
# over the persisted embedding vectors (phx_dm_embedding.vector_preview) — the
# same deterministic-feature-projection vectors used for advisor similarity. Real
# math over real vectors; no precomputed similarity_match edge required.

_VTYPE = {
    "HOUSEHOLD": ("phx_dm_household", "household_name", ["segment", "total_aum", "state"]),
    "ACCOUNT": ("phx_dm_account", "account_name", ["account_type", "current_value", "status"]),
    "ADVISOR": ("phx_dm_advisor", "advisor_name", ["tenure_years", "status"]),
}


def _parse_vector(raw) -> list[float]:
    if isinstance(raw, list):
        return [float(x) for x in raw]
    try:
        return [float(x) for x in json.loads(raw)]
    except Exception:
        return []


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return round(dot / (na * nb), 4) if na and nb else 0.0


def _embeddings_by_entity(store, entity_type: str) -> dict[str, list[float]]:
    out: dict[str, list[float]] = {}
    for attrs in store.vertices.get("phx_dm_embedding", {}).values():
        if str(attrs.get("entity_type")).upper() == entity_type:
            vec = _parse_vector(attrs.get("vector_preview"))
            if vec:
                out[str(attrs.get("entity_id"))] = vec
    return out


def similar_entities(entity_type: str, source_id: str, top_k: int = 3) -> dict:
    """Top-k cosine-nearest entities of the same type to `source_id`, each with a
    similarity score and its display attributes. Returns {source, matches}."""
    entity_type = entity_type.upper()
    store = get_graph_client().store
    vtype, name_attr, extra = _VTYPE.get(entity_type, (None, None, []))
    if not vtype:
        return {"source": None, "matches": []}

    vectors = _embeddings_by_entity(store, entity_type)
    src_vec = vectors.get(source_id)
    if not src_vec:
        return {"source": None, "matches": []}

    def _label(vid: str) -> dict:
        v = store.vertex(vtype, vid) or {}
        return {"entity_id": vid, "name": v.get(name_attr, vid), **{k: v.get(k) for k in extra}}

    scored = [
        {**_label(vid), "similarity": _cosine(src_vec, vec)}
        for vid, vec in vectors.items()
        if vid != source_id
    ]
    scored.sort(key=lambda r: r["similarity"], reverse=True)
    return {
        "source": {**_label(source_id), "vector_dims": len(src_vec)},
        "matches": scored[:top_k],
    }
