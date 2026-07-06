from __future__ import annotations

"""VectorClient adapter for graph-entity embeddings (Section 11.1 §8).

Same house pattern as every other adapter. Scope: advisor/household/account/GNN vectors
ONLY — Chroma (document/RAG vectors) is untouched and out of scope.

  VECTOR_CLIENT_MODE=local        -> LocalVectorClient (SQLite gnn_embeddings + brute-force
                                     cosine; at 1.1K vectors an index would be decoration).
  VECTOR_CLIENT_MODE=tigergraph   -> TigerGraphVectorClient (native EMBEDDING attr + HNSW +
                                     vectorSearch GSQL; TigerVector, TG 4.2+). Support is
                                     verified EMPIRICALLY (scripts/check_tg_vector_support.sh),
                                     never assumed; falls back to local when unavailable.
"""

import json
import math
import sqlite3
from pathlib import Path
from typing import Protocol

from app.config.settings import get_settings


class VectorClientError(RuntimeError):
    pass


class VectorClient(Protocol):
    def upsert_embeddings(self, entity_type: str, model_name: str, model_version: str,
                          vectors: dict[str, list[float]]) -> dict: ...

    def search(self, entity_type: str, vector: list[float], top_k: int = 5,
               exclude_id: str | None = None) -> list[dict]: ...

    def get(self, entity_type: str, entity_id: str) -> list[float] | None: ...

    def describe(self) -> dict: ...


def _cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


class LocalVectorClient:
    """SQLite gnn_embeddings table + brute-force cosine. The deterministic default."""

    def __init__(self) -> None:
        self.db_path = get_settings().sqlite_db_path
        self._init()

    def _init(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS gnn_embeddings (
                    entity_type TEXT, entity_id TEXT, model_name TEXT, model_version TEXT,
                    dim INTEGER, vector_json TEXT, computed_at TEXT,
                    PRIMARY KEY (entity_type, entity_id, model_name))"""
            )

    def upsert_embeddings(self, entity_type, model_name, model_version, vectors) -> dict:
        from datetime import datetime

        now = datetime.now().strftime("%Y-%m-%d")
        with sqlite3.connect(self.db_path) as conn:
            for eid, vec in vectors.items():
                conn.execute(
                    "REPLACE INTO gnn_embeddings VALUES (?,?,?,?,?,?,?)",
                    (entity_type, eid, model_name, model_version, len(vec),
                     json.dumps([round(float(v), 5) for v in vec]), now))
        return {"upserted": len(vectors), "entity_type": entity_type, "model_name": model_name}

    def _rows(self, entity_type: str) -> list[tuple[str, list[float]]]:
        with sqlite3.connect(self.db_path) as conn:
            try:
                rows = conn.execute(
                    "SELECT entity_id, vector_json FROM gnn_embeddings WHERE entity_type=? "
                    "AND model_name='graphsage-v1'", (entity_type.upper(),)).fetchall()
            except sqlite3.OperationalError:
                return []
        out = []
        for eid, vj in rows:
            try:
                out.append((eid, [float(x) for x in json.loads(vj)]))
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
        return out

    def get(self, entity_type, entity_id) -> list[float] | None:
        for eid, vec in self._rows(entity_type):
            if eid == entity_id:
                return vec
        return None

    def search(self, entity_type, vector, top_k=5, exclude_id=None) -> list[dict]:
        scored = [
            {"entity_id": eid, "score": round(_cosine(vector, vec), 4)}
            for eid, vec in self._rows(entity_type) if eid != exclude_id
        ]
        scored.sort(key=lambda r: -r["score"])
        return scored[:top_k]

    def describe(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            try:
                n = conn.execute("SELECT COUNT(*) FROM gnn_embeddings").fetchone()[0]
            except sqlite3.OperationalError:
                n = 0
        return {"mode": "local", "backend": "sqlite+cosine", "vectors": n, "vector_backend_verified": True}


class TigerGraphVectorClient:
    """TigerGraph-native vectors (EMBEDDING attr + HNSW + vectorSearch GSQL). Real support is
    verified empirically before use (scripts/check_tg_vector_support.sh); until then this
    delegates to LocalVectorClient so nothing depends on unverified engine features."""

    def __init__(self) -> None:
        # Empirical support has NOT been confirmed on this 2-core CE 4.2.3 box (same live-TG
        # limit as Phase 2/3). Honest fallback to local; cutover is env-only on a bigger box.
        self._local = LocalVectorClient()
        self._verified = False

    def upsert_embeddings(self, *a, **k):
        return self._local.upsert_embeddings(*a, **k)

    def search(self, *a, **k):
        return self._local.search(*a, **k)

    def get(self, *a, **k):
        return self._local.get(*a, **k)

    def describe(self) -> dict:
        return {"mode": "tigergraph", "backend": "delegating-to-local",
                "vector_backend_verified": self._verified,
                "note": "TigerVector EMBEDDING/HNSW support unconfirmed on this box; see "
                        "scripts/check_tg_vector_support.sh. Local cosine serves in the meantime."}


_vector_client: VectorClient | None = None


def get_vector_client() -> VectorClient:
    global _vector_client
    if _vector_client is None:
        mode = getattr(get_settings(), "vector_client_mode", "local").lower()
        if mode == "local":
            _vector_client = LocalVectorClient()
        elif mode == "tigergraph":
            _vector_client = TigerGraphVectorClient()
        else:
            raise VectorClientError(f"Unknown VECTOR_CLIENT_MODE '{mode}' (expected local|tigergraph)")
    return _vector_client


def reset_vector_client() -> None:
    global _vector_client
    _vector_client = None
