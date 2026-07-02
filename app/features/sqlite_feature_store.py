from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.features.models import FeatureVector


class SQLiteFeatureStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS feature_vectors (
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                features_json TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(entity_type, entity_id)
            )
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS prediction_results (
                prediction_id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                target TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """)
            conn.commit()

    def upsert_feature_vector(self, vector: FeatureVector) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO feature_vectors(entity_type, entity_id, features_json, metadata_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(entity_type, entity_id)
                DO UPDATE SET features_json=excluded.features_json, metadata_json=excluded.metadata_json, updated_at=CURRENT_TIMESTAMP
                """,
                (vector.entity_type, vector.entity_id, json.dumps(vector.features), json.dumps(vector.metadata)),
            )
            conn.commit()

    def get_feature_vector(self, entity_type: str, entity_id: str) -> FeatureVector | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT features_json, metadata_json FROM feature_vectors WHERE entity_type=? AND entity_id=?",
                (entity_type, entity_id),
            ).fetchone()
        if not row:
            return None
        return FeatureVector(entity_type=entity_type, entity_id=entity_id, features=json.loads(row[0]), metadata=json.loads(row[1]))

    def list_feature_vectors(self, entity_type: str | None = None) -> list[FeatureVector]:
        with self._connect() as conn:
            if entity_type:
                rows = conn.execute(
                    "SELECT entity_type, entity_id, features_json, metadata_json FROM feature_vectors WHERE entity_type=?",
                    (entity_type,),
                ).fetchall()
            else:
                rows = conn.execute("SELECT entity_type, entity_id, features_json, metadata_json FROM feature_vectors").fetchall()
        return [
            FeatureVector(entity_type=row[0], entity_id=row[1], features=json.loads(row[2]), metadata=json.loads(row[3]))
            for row in rows
        ]

    def save_prediction(self, prediction_id: str, entity_type: str, entity_id: str, target: str, result: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO prediction_results(prediction_id, entity_type, entity_id, target, result_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (prediction_id, entity_type, entity_id, target, json.dumps(result)),
            )
            conn.commit()

    def count(self) -> dict[str, int]:
        with self._connect() as conn:
            features = conn.execute("SELECT COUNT(*) FROM feature_vectors").fetchone()[0]
            predictions = conn.execute("SELECT COUNT(*) FROM prediction_results").fetchone()[0]
        return {"feature_vectors": int(features), "prediction_results": int(predictions)}
