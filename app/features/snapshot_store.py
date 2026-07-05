from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.config.settings import get_settings
from app.features.engineering import FeatureSnapshot


class SnapshotStore:
    """SQLite persistence for feature snapshots, including per-feature lineage."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or get_settings().sqlite_db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS feature_snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    snapshot_time TEXT NOT NULL,
                    feature_version TEXT NOT NULL,
                    features_json TEXT NOT NULL,
                    lineage_json TEXT NOT NULL
                )"""
            )

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def save(self, snapshot: FeatureSnapshot) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO feature_snapshots VALUES (?,?,?,?,?,?,?)",
                (
                    snapshot.snapshot_id,
                    snapshot.entity_type,
                    snapshot.entity_id,
                    snapshot.snapshot_time,
                    snapshot.feature_version,
                    json.dumps(snapshot.values()),
                    json.dumps(snapshot.lineage()),
                ),
            )

    def get(self, snapshot_id: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT snapshot_id, entity_type, entity_id, snapshot_time, feature_version, features_json, lineage_json "
                "FROM feature_snapshots WHERE snapshot_id = ?",
                (snapshot_id,),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def latest_for_entity(self, entity_type: str, entity_id: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT snapshot_id, entity_type, entity_id, snapshot_time, feature_version, features_json, lineage_json "
                "FROM feature_snapshots WHERE entity_type = ? AND entity_id = ? "
                "ORDER BY snapshot_time DESC, snapshot_id DESC LIMIT 1",
                (entity_type, entity_id),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def list_snapshots(self, entity_type: str | None = None, limit: int = 100) -> list[dict]:
        query = (
            "SELECT snapshot_id, entity_type, entity_id, snapshot_time, feature_version, features_json, lineage_json "
            "FROM feature_snapshots"
        )
        params: tuple = ()
        if entity_type:
            query += " WHERE entity_type = ?"
            params = (entity_type,)
        query += " ORDER BY snapshot_time DESC LIMIT ?"
        params += (limit,)
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_dict(row) for row in rows]

    @staticmethod
    def _row_to_dict(row: tuple) -> dict:
        return {
            "snapshot_id": row[0],
            "entity_type": row[1],
            "entity_id": row[2],
            "snapshot_time": row[3],
            "feature_version": row[4],
            "features": json.loads(row[5]),
            "lineage": json.loads(row[6]),
        }
