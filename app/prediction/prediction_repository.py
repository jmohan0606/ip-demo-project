from __future__ import annotations

import json
from app.feature_store.sqlite_manager import SQLiteManager
from app.models.predictions import PredictionRecord


class PredictionRepository:
    def __init__(self) -> None:
        self.db = SQLiteManager()
        self.initialize()

    def initialize(self) -> None:
        self.db.initialize_foundation_tables()
        with self.db.connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS phx_dm_local_prediction_result (
                    prediction_id TEXT PRIMARY KEY,
                    entity_type TEXT,
                    entity_id TEXT,
                    prediction_type TEXT,
                    score REAL,
                    label TEXT,
                    model_name TEXT,
                    model_version TEXT,
                    confidence REAL,
                    explanation TEXT,
                    feature_snapshot_json TEXT,
                    generated_ts TEXT,
                    status TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_phx_dm_prediction_entity
                ON phx_dm_local_prediction_result(entity_type, entity_id, prediction_type)
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS phx_dm_model_metadata (
                    model_key TEXT PRIMARY KEY,
                    model_name TEXT,
                    model_version TEXT,
                    model_type TEXT,
                    training_summary_json TEXT,
                    created_ts TEXT
                )
            """)
            conn.commit()

    def save_prediction(self, prediction: PredictionRecord) -> None:
        with self.db.connect() as conn:
            conn.execute("""
                INSERT INTO phx_dm_local_prediction_result (
                    prediction_id, entity_type, entity_id, prediction_type, score, label,
                    model_name, model_version, confidence, explanation, feature_snapshot_json,
                    generated_ts, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(prediction_id) DO UPDATE SET
                    score=excluded.score,
                    label=excluded.label,
                    explanation=excluded.explanation,
                    generated_ts=excluded.generated_ts
            """, (
                prediction.prediction_id, prediction.entity_type, prediction.entity_id,
                prediction.prediction_type.value, prediction.score, prediction.label,
                prediction.model_name, prediction.model_version, prediction.confidence,
                prediction.explanation, json.dumps(prediction.feature_snapshot),
                prediction.generated_ts.isoformat(), prediction.status
            ))
            conn.commit()

    def save_model_metadata(self, model_key: str, metadata: dict) -> None:
        with self.db.connect() as conn:
            conn.execute("""
                INSERT INTO phx_dm_model_metadata (
                    model_key, model_name, model_version, model_type, training_summary_json, created_ts
                )
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(model_key) DO UPDATE SET
                    training_summary_json=excluded.training_summary_json,
                    created_ts=CURRENT_TIMESTAMP
            """, (
                model_key,
                metadata.get("model_name"),
                metadata.get("model_version"),
                metadata.get("model_type"),
                json.dumps(metadata),
            ))
            conn.commit()

    def list_predictions(self, entity_id: str | None = None, prediction_type: str | None = None, limit: int = 100) -> list[dict]:
        sql = "SELECT * FROM phx_dm_local_prediction_result WHERE 1=1"
        params = []
        if entity_id:
            sql += " AND entity_id = ?"
            params.append(entity_id)
        if prediction_type:
            sql += " AND prediction_type = ?"
            params.append(prediction_type)
        sql += " ORDER BY generated_ts DESC LIMIT ?"
        params.append(limit)
        rows = self.db.query(sql, tuple(params))
        for row in rows:
            row["feature_snapshot"] = json.loads(row.pop("feature_snapshot_json") or "{}")
        return rows

    def counts(self) -> list[dict]:
        return self.db.query("""
            SELECT prediction_type, label, COUNT(*) AS prediction_count
            FROM phx_dm_local_prediction_result
            GROUP BY prediction_type, label
            ORDER BY prediction_type, prediction_count DESC
        """)

    def model_metadata(self) -> list[dict]:
        rows = self.db.query("SELECT * FROM phx_dm_model_metadata ORDER BY created_ts DESC")
        for row in rows:
            row["training_summary"] = json.loads(row.pop("training_summary_json") or "{}")
        return rows
