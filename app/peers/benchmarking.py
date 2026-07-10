from __future__ import annotations

import logging

from app.graph.client import get_graph_client
from app.graph.queries.common import (
    graph_fallback_store,
    resolve_scope_advisor_ids_graph,
    run_catalog_query,
    scope_advisor_placements,
)
from app.features.snapshot_store import SnapshotStore
from app.embeddings.service import EmbeddingSimilarityService

logger = logging.getLogger(__name__)

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

# wide-open DATETIME window for GQ-008 when we only need peer identities
_DATE_MIN = "1900-01-01 00:00:00"
_DATE_MAX = "2100-01-01 00:00:00"


class PeerBenchmarkingService:
    """Benchmarks one advisor against a REAL peer group (the advisors resolved
    under the current scope) using percentile ranks of their actual feature
    snapshots, plus the advisor's nearest peers from the real similarity model.
    No synthetic benchmarks — the peer curve is the live distribution."""

    def __init__(self) -> None:
        self._graph = get_graph_client()
        self._snaps = SnapshotStore()

    def _features(self, advisor_id: str) -> dict:
        snap = self._snaps.latest_for_entity("ADVISOR", advisor_id)
        return (snap or {}).get("features", {}) if snap else {}

    def _name_store(self, advisor_id: str) -> str:
        """LOGGED local-store fallback for advisor display names — only used when
        the catalogued queries (GQ-053 / GQ-008) did not cover this advisor."""
        logger.warning(
            "advisor name for %s not resolved via catalogued queries — "
            "falling back to local store traversal",
            advisor_id,
        )
        store = graph_fallback_store(self._graph)
        return str((store.vertex("phx_dm_advisor", advisor_id) or {}).get("advisor_name") or advisor_id)

    def _similarity_peer_names(self, advisor_id: str) -> dict[str, str]:
        """advisor_id -> advisor_name for the advisor's similarity peers via
        GQ-008 get_peer_benchmark (peer_method=SIMILARITY, open date window)."""
        results = run_catalog_query(
            self._graph,
            "get_peer_benchmark",
            {
                "advisor_id": str(advisor_id),
                "peer_method": "SIMILARITY",
                "start_date": _DATE_MIN,
                "end_date": _DATE_MAX,
            },
        )
        names: dict[str, str] = {}
        for entry in results or []:
            for peer in entry.get("peers", []) or []:
                attrs = peer.get("attributes", peer)
                pid = str(attrs.get("advisor_id") or peer.get("v_id") or "")
                pname = attrs.get("advisor_name")
                if pid and pname:
                    names[pid] = str(pname)
        return names

    @staticmethod
    def _num(f: dict, key: str) -> float:
        v = f.get(key)
        return float(v) if v is not None else 0.0

    def benchmark(self, advisor_id: str, scope_type: str = "FIRM", scope_id: str = "F001") -> dict:
        scope_type_u = (scope_type or "FIRM").upper()
        # scope -> advisor ids via GQ-002 get_scope_descendants (logged store fallback inside)
        peer_ids = resolve_scope_advisor_ids_graph(self._graph, scope_type_u, scope_id)
        if advisor_id not in peer_ids:
            peer_ids = sorted(set(peer_ids) | {advisor_id})

        # advisor display names via GQ-053 get_scope_advisor_placements
        placements = scope_advisor_placements(self._graph, scope_type_u, scope_id)
        names: dict[str, str] = {}
        if placements is not None:
            names = {
                aid: str(attrs.get("advisor_name") or aid)
                for aid, attrs in placements.items()
                if attrs.get("advisor_name")
            }
        else:
            logger.warning(
                "get_scope_advisor_placements unavailable for %s/%s — advisor names "
                "will use the logged local store fallback",
                scope_type_u, scope_id,
            )

        def name_of(aid: str) -> str:
            got = names.get(aid)
            if got:
                return got
            # single-advisor GQ-053 lookup (scope_type=ADVISOR) before any store fallback
            single = scope_advisor_placements(self._graph, "ADVISOR", aid)
            if single and single.get(aid, {}).get("advisor_name"):
                names[aid] = str(single[aid]["advisor_name"])
                return names[aid]
            return self._name_store(aid)

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
        matches = (similar.get("matches", []) if isinstance(similar, dict) else [])[:6]

        # cover any nearest peer outside the scope's placement map via GQ-008
        missing = [m.get("target_entity_id") for m in matches if m.get("target_entity_id") not in names]
        if missing:
            names.update({
                aid: nm for aid, nm in self._similarity_peer_names(advisor_id).items()
                if aid not in names
            })

        nearest = []
        for m in matches:
            tid = m.get("target_entity_id")
            nearest.append({
                "advisor_id": tid,
                "advisor_name": name_of(tid),
                "similarity_score": m.get("similarity_score"),
                "reasons": m.get("reason_features") or m.get("reason_json") or [],
                "revenue_ltm": round(self._num(peer_features.get(tid) or self._features(tid), "revenue_ltm"), 2),
            })

        return {
            "advisor_id": advisor_id,
            "advisor_name": name_of(advisor_id),
            "scope_type": scope_type_u,
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
