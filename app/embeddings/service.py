from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import struct
from pathlib import Path

from app.config.settings import get_settings
from app.features.engineering import FeatureEngineeringService
from app.features.snapshot_store import SnapshotStore
from app.graph.client import GraphClient, get_graph_client

EMBEDDING_MODEL = "deterministic-feature-projection"
EMBEDDING_VERSION = "v2.0"
EMBEDDING_DIM = 8

# Stable numeric features used as the embedding input vector (spec Section 10).
PROJECTION_FEATURES = [
    "revenue_ltm",
    "revenue_growth_3m_pct",
    "managed_revenue_ratio",
    "product_diversification_score",
    "household_count",
    "aum_total",
    "nnm_3m",
    "ncf_3m",
    "lead_conversion_rate",
    "referral_conversion_rate",
    "crm_pipeline_value",
    "agp_risk_score",
    "kpi_on_track_ratio",
    "advisor_degree_centrality",
    "client_value_score",
    "time_sensitivity_score",
]


def _projection_matrix() -> list[list[float]]:
    """Versioned deterministic projection: coefficients derived from a hash of
    (model, version, dim, feature name) — stable across runs and machines."""
    matrix: list[list[float]] = []
    for dim in range(EMBEDDING_DIM):
        row = []
        for feature_name in PROJECTION_FEATURES:
            digest = hashlib.sha256(f"{EMBEDDING_MODEL}:{EMBEDDING_VERSION}:{dim}:{feature_name}".encode()).digest()
            (value,) = struct.unpack(">q", digest[:8])
            row.append((value % 2_000_001 - 1_000_000) / 1_000_000)  # [-1, 1]
        matrix.append(row)
    return matrix


class EmbeddingSimilarityService:
    """Spec Section 10: normalized feature vector -> versioned deterministic
    projection -> persisted embedding -> cosine similarity -> persisted top
    matches with reason features. Explicitly a simulation; a future GNN swaps
    only the projection step."""

    def __init__(self, graph: GraphClient | None = None) -> None:
        self.graph = graph or get_graph_client()
        self.snapshots = SnapshotStore()
        self.db_path = get_settings().sqlite_db_path
        self._init_tables()

    def _init_tables(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS embeddings (
                    embedding_id TEXT PRIMARY KEY, entity_type TEXT, entity_id TEXT,
                    model_name TEXT, model_version TEXT, dimensions INTEGER,
                    vector_json TEXT, source_snapshot_id TEXT, generated_at TEXT)"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS similarity_matches (
                    similarity_id TEXT PRIMARY KEY, entity_type TEXT,
                    source_entity_id TEXT, target_entity_id TEXT,
                    similarity_score REAL, reason_json TEXT, model_version TEXT, generated_at TEXT)"""
            )

    # -- snapshot collection --

    def _ensure_snapshots(self, advisor_ids: list[str]) -> dict[str, dict]:
        engine = FeatureEngineeringService(self.graph)
        snapshots: dict[str, dict] = {}
        for advisor_id in advisor_ids:
            existing = self.snapshots.latest_for_entity("ADVISOR", advisor_id)
            if existing is None:
                snapshot = engine.compute_advisor_snapshot(advisor_id)
                engine.persist_snapshot(snapshot)
                existing = self.snapshots.latest_for_entity("ADVISOR", advisor_id)
            else:
                engine.ensure_graph_artifact(existing)
            snapshots[advisor_id] = existing
        return snapshots

    def _all_advisor_ids(self) -> list[str]:
        merged: dict = {}
        for entry in self.graph.run_query(
            "get_scope_descendants", {"scope_type": "ALL", "scope_id": "", "entity_type": "ADVISOR"}
        ).get("results", []):
            merged.update(entry)
        return sorted(v["v_id"] for v in merged.get("advisor_descendants", []))

    # -- embedding build --

    def build_advisor_embeddings(self, advisor_ids: list[str] | None = None) -> dict:
        advisor_ids = advisor_ids or self._all_advisor_ids()
        snapshots = self._ensure_snapshots(advisor_ids)

        # cohort min-max normalization per feature
        columns: dict[str, list[float]] = {name: [] for name in PROJECTION_FEATURES}
        for snap in snapshots.values():
            for name in PROJECTION_FEATURES:
                value = snap["features"].get(name)
                columns[name].append(float(value) if value is not None else 0.0)
        bounds = {name: (min(vals), max(vals)) for name, vals in columns.items()}

        matrix = _projection_matrix()
        generated_at = list(snapshots.values())[0]["snapshot_time"] if snapshots else None
        embeddings: dict[str, list[float]] = {}
        for advisor_id, snap in snapshots.items():
            normalized = []
            for name in PROJECTION_FEATURES:
                value = snap["features"].get(name)
                value = float(value) if value is not None else 0.0
                low, high = bounds[name]
                normalized.append((value - low) / (high - low) if high > low else 0.0)
            vector = [round(sum(w * x for w, x in zip(row, normalized)), 6) for row in matrix]
            norm = math.sqrt(sum(v * v for v in vector)) or 1.0
            vector = [round(v / norm, 6) for v in vector]
            embeddings[advisor_id] = vector
            self._persist_embedding(advisor_id, vector, snap["snapshot_id"], generated_at)

        return {
            "model": EMBEDDING_MODEL,
            "version": EMBEDDING_VERSION,
            "dimensions": EMBEDDING_DIM,
            "advisors_embedded": len(embeddings),
            "note": "Deterministic simulation — a future GNN/graph-ML implementation replaces only the projection step.",
        }

    def _persist_embedding(self, advisor_id: str, vector: list[float], snapshot_id: str, generated_at: str | None) -> None:
        embedding_id = f"EMB_{advisor_id}_{EMBEDDING_VERSION}"
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO embeddings VALUES (?,?,?,?,?,?,?,?,?)",
                (embedding_id, "ADVISOR", advisor_id, EMBEDDING_MODEL, EMBEDDING_VERSION,
                 EMBEDDING_DIM, json.dumps(vector), snapshot_id, generated_at),
            )
        entry = {
            "kind": "vertex", "target": "phx_dm_embedding", "id_column": "embedding_id", "file": "runtime",
            "columns": {c: c for c in ("embedding_id", "entity_type", "entity_id", "model_name",
                                        "model_version", "dimensions", "vector_preview", "generated_at")},
        }
        self.graph.upsert(entry, [{
            "embedding_id": embedding_id, "entity_type": "ADVISOR", "entity_id": advisor_id,
            "model_name": EMBEDDING_MODEL, "model_version": EMBEDDING_VERSION,
            "dimensions": EMBEDDING_DIM, "vector_preview": json.dumps(vector), "generated_at": generated_at,
        }])
        self.graph.upsert(
            {"kind": "edge", "target": "phx_dm_advisor_has_embedding", "from_type": "phx_dm_advisor",
             "to_type": "phx_dm_embedding", "from_column": "from_id", "to_column": "to_id", "file": "runtime",
             "columns": {}},
            [{"from_id": advisor_id, "to_id": embedding_id}],
        )

    # -- similarity --

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a)) or 1.0
        nb = math.sqrt(sum(y * y for y in b)) or 1.0
        return dot / (na * nb)

    def _load_embeddings(self) -> dict[str, list[float]]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT entity_id, vector_json FROM embeddings WHERE model_version = ?", (EMBEDDING_VERSION,)
            ).fetchall()
        return {entity_id: json.loads(vector) for entity_id, vector in rows}

    def _reason_features(self, source_id: str, target_id: str, top_n: int = 4) -> list[str]:
        """Features where source and target are cohort-closest — the 'why similar'."""
        source = self.snapshots.latest_for_entity("ADVISOR", source_id)
        target = self.snapshots.latest_for_entity("ADVISOR", target_id)
        if not source or not target:
            return []
        deltas = []
        for name in PROJECTION_FEATURES:
            sv, tv = source["features"].get(name), target["features"].get(name)
            if sv is None or tv is None:
                continue
            scale = max(abs(float(sv)), abs(float(tv)), 1e-9)
            deltas.append((abs(float(sv) - float(tv)) / scale, name))
        deltas.sort()
        return [name for _, name in deltas[:top_n]]

    def build_similarity_matches(self, top_k: int = 5, min_score: float = 0.0) -> dict:
        embeddings = self._load_embeddings()
        if not embeddings:
            raise RuntimeError("No embeddings built yet — call build_advisor_embeddings first")
        generated = 0
        for source_id, source_vec in embeddings.items():
            scored = [
                (self._cosine(source_vec, target_vec), target_id)
                for target_id, target_vec in embeddings.items()
                if target_id != source_id
            ]
            scored.sort(reverse=True)
            for score, target_id in scored[:top_k]:
                if score < min_score:
                    continue
                self._persist_match(source_id, target_id, round(score, 4))
                generated += 1
        return {"matches_persisted": generated, "top_k": top_k, "advisors": len(embeddings)}

    def _persist_match(self, source_id: str, target_id: str, score: float) -> None:
        similarity_id = f"SIM_{source_id}_{target_id}_{EMBEDDING_VERSION}"
        reasons = self._reason_features(source_id, target_id)
        generated_at = None
        source_snap = self.snapshots.latest_for_entity("ADVISOR", source_id)
        if source_snap:
            generated_at = source_snap["snapshot_time"]
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO similarity_matches VALUES (?,?,?,?,?,?,?,?)",
                (similarity_id, "ADVISOR", source_id, target_id, score, json.dumps(reasons),
                 EMBEDDING_VERSION, generated_at),
            )
        entry = {
            "kind": "vertex", "target": "phx_dm_similarity_match", "id_column": "similarity_id", "file": "runtime",
            "columns": {c: c for c in ("similarity_id", "entity_type", "source_entity_id", "target_entity_id",
                                        "model_version", "similarity_score", "reason_json", "generated_at")},
        }
        self.graph.upsert(entry, [{
            "similarity_id": similarity_id, "entity_type": "ADVISOR", "source_entity_id": source_id,
            "target_entity_id": target_id, "model_version": EMBEDDING_VERSION,
            "similarity_score": score, "reason_json": json.dumps(reasons), "generated_at": generated_at,
        }])
        for edge, from_id, to_id in [
            ("phx_dm_advisor_has_similarity_match", source_id, similarity_id),
            ("phx_dm_similarity_match_targets_advisor", similarity_id, target_id),
        ]:
            from_type = "phx_dm_advisor" if edge.startswith("phx_dm_advisor") else "phx_dm_similarity_match"
            to_type = "phx_dm_similarity_match" if edge.endswith("similarity_match") else "phx_dm_advisor"
            self.graph.upsert(
                {"kind": "edge", "target": edge, "from_type": from_type, "to_type": to_type,
                 "from_column": "from_id", "to_column": "to_id", "file": "runtime", "columns": {}},
                [{"from_id": from_id, "to_id": to_id}],
            )

    def projection(self, advisor_id: str, top_k: int = 5) -> dict:
        """Real 2D dimensionality reduction (PCA) of the persisted advisor
        embedding vectors — every point is a real vector from the embeddings
        table, projected 8D -> 2D. No fabricated coordinates. The target advisor
        and its top-k cosine-similar peers are role-tagged for the scatter."""
        from sklearn.decomposition import PCA

        embeddings = self._load_embeddings()
        if not embeddings:
            self.build_advisor_embeddings()
            embeddings = self._load_embeddings()
        ids = sorted(embeddings)
        matrix = [embeddings[i] for i in ids]

        similar_ids = {
            m["target_entity_id"] for m in self.similar_advisors(advisor_id, top_k)["matches"]
        }
        sim_scores = {
            m["target_entity_id"]: m["similarity_score"]
            for m in self.similar_advisors(advisor_id, top_k)["matches"]
        }

        pca = PCA(n_components=2, random_state=0)
        coords = pca.fit_transform(matrix)

        points = []
        for advisor, (x, y) in zip(ids, coords):
            role = "target" if advisor == advisor_id else ("similar" if advisor in similar_ids else "other")
            points.append({
                "advisor_id": advisor,
                "x": round(float(x), 4),
                "y": round(float(y), 4),
                "role": role,
                "similarity": sim_scores.get(advisor),
            })
        return {
            "advisor_id": advisor_id,
            "model": EMBEDDING_MODEL,
            "version": EMBEDDING_VERSION,
            "source_dimensions": EMBEDDING_DIM,
            "reduction": "PCA",
            "explained_variance_ratio": [round(float(v), 4) for v in pca.explained_variance_ratio_],
            "point_count": len(points),
            "points": points,
        }

    def similar_advisors(self, advisor_id: str, top_k: int = 5) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT target_entity_id, similarity_score, reason_json FROM similarity_matches "
                "WHERE source_entity_id = ? AND model_version = ? ORDER BY similarity_score DESC LIMIT ?",
                (advisor_id, EMBEDDING_VERSION, top_k),
            ).fetchall()
        return {
            "advisor_id": advisor_id,
            "model": EMBEDDING_MODEL,
            "version": EMBEDDING_VERSION,
            "matches": [
                {"target_entity_id": target, "similarity_score": score, "reason_features": json.loads(reasons)}
                for target, score, reasons in rows
            ],
            "simulation_note": "Deterministic feature-projection similarity — not a trained GNN.",
        }
