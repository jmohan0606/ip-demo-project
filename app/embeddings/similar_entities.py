from __future__ import annotations

import json
import logging
import math

from app.graph.client import get_graph_client
from app.graph.queries.common import graph_fallback_store, run_catalog_query

logger = logging.getLogger(__name__)

# Extends the existing advisor similarity capability to other entity types
# (household, account, portfolio) by computing cosine nearest-neighbours directly
# over the persisted embedding vectors (phx_dm_embedding.vector_preview) — the
# same deterministic-feature-projection vectors used for advisor similarity. Real
# math over real vectors; no precomputed similarity_match edge required. Vectors
# and display attributes come from GQ-054 get_embeddings_by_type via run_query
# (real TigerGraph in real mode); the in-memory store scan below survives only as
# the logged fallback path.

_VTYPE = {
    "HOUSEHOLD": ("phx_dm_household", "household_name", ["segment", "total_aum", "state"]),
    "ACCOUNT": ("phx_dm_account", "account_name", ["account_type", "current_value", "status"]),
    "ADVISOR": ("phx_dm_advisor", "advisor_name", ["tenure_years", "status"]),
}

# GQ-054 result key holding the display vertices for each entity type
_ENTITY_SET_KEY = {"HOUSEHOLD": "households", "ACCOUNT": "accounts", "ADVISOR": "advisors"}


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
    """Logged-fallback-only store scan (pre-migration read path, kept verbatim)."""
    out: dict[str, list[float]] = {}
    for attrs in store.vertices.get("phx_dm_embedding", {}).values():
        if str(attrs.get("entity_type")).upper() == entity_type:
            vec = _parse_vector(attrs.get("vector_preview"))
            if vec:
                out[str(attrs.get("entity_id"))] = vec
    return out


def _load_type_data(graph, entity_type: str) -> tuple[dict[str, list[float]], dict[str, dict] | None]:
    """(entity_id -> vector, entity_id -> display attrs | None) for the type.

    Primary path: GQ-054 get_embeddings_by_type through run_query. Fallback
    (logged by run_catalog_query): the original in-memory store scan, with
    display attrs read per-vertex from the store (attrs map returned as None).
    """
    results = run_catalog_query(graph, "get_embeddings_by_type", {"entity_type": entity_type})
    if results is not None:
        for entry in results:
            embeddings = entry.get("embeddings")
            if embeddings is None:
                continue
            vectors: dict[str, list[float]] = {}
            for row in embeddings:
                attrs = row.get("attributes", row)
                vec = _parse_vector(attrs.get("vector_preview"))
                if vec:
                    vectors[str(attrs.get("entity_id"))] = vec
            entity_attrs = {
                str(row.get("v_id")): row.get("attributes", {})
                for row in entry.get(_ENTITY_SET_KEY.get(entity_type, ""), [])
            }
            return vectors, entity_attrs
        logger.warning(
            "get_embeddings_by_type returned no embeddings entry for %s — "
            "falling back to local store traversal", entity_type,
        )
    return _embeddings_by_entity(graph_fallback_store(graph), entity_type), None


def similar_entities(entity_type: str, source_id: str, top_k: int = 3) -> dict:
    """Top-k cosine-nearest entities of the same type to `source_id`, each with a
    similarity score and its display attributes. Returns {source, matches}."""
    entity_type = entity_type.upper()
    graph = get_graph_client()
    vtype, name_attr, extra = _VTYPE.get(entity_type, (None, None, []))
    if not vtype:
        return {"source": None, "matches": []}

    vectors, entity_attrs = _load_type_data(graph, entity_type)
    src_vec = vectors.get(source_id)
    if not src_vec:
        return {"source": None, "matches": []}

    def _label(vid: str) -> dict:
        if entity_attrs is not None:
            v = entity_attrs.get(vid, {})
        else:  # logged store fallback path
            v = graph_fallback_store(graph).vertex(vtype, vid) or {}
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
