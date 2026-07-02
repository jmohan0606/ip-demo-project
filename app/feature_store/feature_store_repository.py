from __future__ import annotations

import json
from app.feature_store.sqlite_manager import SQLiteManager
from app.models.features import FeatureDefinition, FeatureVector


class FeatureStoreRepository:
    def __init__(self) -> None:
        self.db = SQLiteManager()
        self.initialize()

    def initialize(self) -> None:
        self.db.initialize_foundation_tables()
        with self.db.connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS phx_dm_feature_definition (
                    feature_name TEXT PRIMARY KEY,
                    feature_group TEXT,
                    entity_type TEXT,
                    description TEXT,
                    data_type TEXT,
                    version TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS phx_dm_feature_vector (
                    entity_type TEXT,
                    entity_id TEXT,
                    feature_group TEXT,
                    feature_version TEXT,
                    features_json TEXT,
                    created_at TEXT,
                    PRIMARY KEY (entity_type, entity_id, feature_group, feature_version)
                )
            """)
            conn.commit()

    def save_definition(self, definition: FeatureDefinition) -> None:
        with self.db.connect() as conn:
            conn.execute("""
                INSERT INTO phx_dm_feature_definition (
                    feature_name, feature_group, entity_type, description, data_type, version
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(feature_name) DO UPDATE SET
                    description=excluded.description,
                    version=excluded.version
            """, (
                definition.feature_name,
                definition.feature_group.value,
                definition.entity_type.value,
                definition.description,
                definition.data_type,
                definition.version,
            ))
            conn.commit()

    def save_feature_vector(self, vector: FeatureVector) -> None:
        with self.db.connect() as conn:
            conn.execute("""
                INSERT INTO phx_dm_feature_vector (
                    entity_type, entity_id, feature_group, feature_version, features_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(entity_type, entity_id, feature_group, feature_version) DO UPDATE SET
                    features_json=excluded.features_json,
                    created_at=excluded.created_at
            """, (
                vector.entity_type.value,
                vector.entity_id,
                vector.feature_group.value,
                vector.feature_version,
                json.dumps(vector.features),
                vector.created_at.isoformat(),
            ))
            conn.commit()

    def get_feature_vector(self, entity_type: str, entity_id: str, feature_group: str) -> dict | None:
        rows = self.db.query("""
            SELECT * FROM phx_dm_feature_vector
            WHERE entity_type = ? AND entity_id = ? AND feature_group = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (entity_type, entity_id, feature_group))
        if not rows:
            return None
        row = rows[0]
        return {
            "entity_type": row["entity_type"],
            "entity_id": row["entity_id"],
            "feature_group": row["feature_group"],
            "feature_version": row["feature_version"],
            "features": json.loads(row["features_json"]),
            "created_at": row["created_at"],
        }

    def list_vectors(self, feature_group: str | None = None, limit: int = 100) -> list[dict]:
        if feature_group:
            rows = self.db.query("""
                SELECT * FROM phx_dm_feature_vector
                WHERE feature_group = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (feature_group, limit))
        else:
            rows = self.db.query("""
                SELECT * FROM phx_dm_feature_vector
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
        out = []
        for row in rows:
            out.append({
                "entity_type": row["entity_type"],
                "entity_id": row["entity_id"],
                "feature_group": row["feature_group"],
                "feature_version": row["feature_version"],
                "features": json.loads(row["features_json"]),
                "created_at": row["created_at"],
            })
        return out

    def feature_counts(self) -> list[dict]:
        return self.db.query("""
            SELECT feature_group, entity_type, COUNT(*) AS vector_count
            FROM phx_dm_feature_vector
            GROUP BY feature_group, entity_type
            ORDER BY vector_count DESC
        """)
