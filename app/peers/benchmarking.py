from __future__ import annotations

from app.graph.client import get_graph_client
from app.graph.queries.common import resolve_scope_advisor_ids
from app.features.snapshot_store import SnapshotStore
from app.embeddings.service import EmbeddingSimilarityService

# radar dimensions: (feature key, display label). All are higher-is-better so a
# larger radar area = stronger advisor. Values are percentile-ranked within the
# peer group, so the chart is scale-free and comparable across metrics.
_DIMENSIONS = [
    ("revenue_ltm", "Revenue"),
    ("aum_total", "AUM"),
    ("kpi_on_track_ratio", "Goal Attainment"),
    ("client_value_score", "Client Value"),
    ("product_diversification_score", "Product Mix"),
    ("lead_conversion_rate", "Lead Conversion"),
]


class PeerBenchmarkingService:
    """Benchmarks one advisor against a REAL peer group (the advisors resolved
    under the current scope) using percentile ranks of their actual feature
    snapshots, plus the advisor's nearest peers from the real similarity model.
    No synthetic benchmarks — the peer curve is the live distribution."""

    def __init__(self) -> None:
        self._store = get_graph_client().store
        self._snaps = SnapshotStore()

    def _features(self, advisor_id: str) -> dict:
        snap = self._snaps.latest_for_entity("ADVISOR", advisor_id)
        return (snap or {}).get("features", {}) if snap else {}

    def _name(self, advisor_id: str) -> str:
        return str((self._store.vertex("phx_dm_advisor", advisor_id) or {}).get("advisor_name") or advisor_id)

    @staticmethod
    def _num(f: dict, key: str) -> float:
        v = f.get(key)
        return float(v) if v is not None else 0.0

    def benchmark(self, advisor_id: str, scope_type: str = "FIRM", scope_id: str = "F001") -> dict:
        peer_ids = resolve_scope_advisor_ids(self._store, (scope_type or "FIRM").upper(), scope_id)
        if advisor_id not in peer_ids:
            peer_ids = sorted(set(peer_ids) | {advisor_id})

        # feature vectors for every advisor in the peer group
        peer_features = {aid: self._features(aid) for aid in peer_ids}
        focal = peer_features.get(advisor_id, {})

        dimensions = []
        for key, label in _DIMENSIONS:
            values = sorted(self._num(f, key) for f in peer_features.values() if f)
            focal_val = self._num(focal, key)
            # percentile = share of peers at or below the focal value
            below = sum(1 for v in values if v <= focal_val)
            percentile = round(below / len(values) * 100, 1) if values else 0.0
            median = values[len(values) // 2] if values else 0.0
            dimensions.append({
                "metric": label,
                "feature": key,
                "advisor_percentile": percentile,
                "peer_median_percentile": 50.0,
                "advisor_value": round(focal_val, 2),
                "peer_median_value": round(median, 2),
            })

        # real nearest peers from the similarity model (ranked, with reasons)
        similar = EmbeddingSimilarityService().similar_advisors(advisor_id, top_k=6)
        nearest = []
        for m in (similar.get("matches", []) if isinstance(similar, dict) else [])[:6]:
            tid = m.get("target_entity_id")
            nearest.append({
                "advisor_id": tid,
                "advisor_name": self._name(tid),
                "similarity_score": m.get("similarity_score"),
                "reasons": m.get("reason_features") or m.get("reason_json") or [],
                "revenue_ltm": round(self._num(peer_features.get(tid) or self._features(tid), "revenue_ltm"), 2),
            })

        return {
            "advisor_id": advisor_id,
            "advisor_name": self._name(advisor_id),
            "scope_type": (scope_type or "FIRM").upper(),
            "scope_id": scope_id,
            "peer_group_size": len(peer_ids),
            "dimensions": dimensions,
            "nearest_peers": nearest,
            "evidence": {
                "source": "percentile rank of the advisor's feature snapshot within the scope's peer group; "
                          "nearest peers from the deterministic similarity model (v2.0)",
                "peer_ids_resolved": len(peer_ids),
            },
        }
