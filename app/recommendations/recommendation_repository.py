from __future__ import annotations

import json
from app.feature_store.sqlite_manager import SQLiteManager
from app.models.recommendations import RecommendationRecord, RecommendationStatus


class RecommendationRepository:
    def __init__(self) -> None:
        self.db = SQLiteManager()
        self.initialize()

    def initialize(self) -> None:
        self.db.initialize_foundation_tables()
        with self.db.connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS phx_dm_local_recommendation (
                    recommendation_id TEXT PRIMARY KEY,
                    entity_type TEXT,
                    entity_id TEXT,
                    household_id TEXT,
                    opportunity_id TEXT,
                    prediction_id TEXT,
                    playbook_id TEXT,
                    recommendation_type TEXT,
                    title TEXT,
                    action_text TEXT,
                    rationale TEXT,
                    score REAL,
                    confidence REAL,
                    status TEXT,
                    compliance_status TEXT,
                    supporting_documents_json TEXT,
                    evidence_json TEXT,
                    reasoning_steps_json TEXT,
                    created_ts TEXT,
                    updated_ts TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_phx_dm_recommendation_entity
                ON phx_dm_local_recommendation(entity_type, entity_id, recommendation_type, status)
            """)
            conn.commit()

    def save_recommendation(self, rec: RecommendationRecord) -> None:
        with self.db.connect() as conn:
            conn.execute("""
                INSERT INTO phx_dm_local_recommendation (
                    recommendation_id, entity_type, entity_id, household_id, opportunity_id,
                    prediction_id, playbook_id, recommendation_type, title, action_text,
                    rationale, score, confidence, status, compliance_status,
                    supporting_documents_json, evidence_json, reasoning_steps_json,
                    created_ts, updated_ts
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(recommendation_id) DO UPDATE SET
                    action_text=excluded.action_text,
                    rationale=excluded.rationale,
                    score=excluded.score,
                    confidence=excluded.confidence,
                    status=excluded.status,
                    updated_ts=excluded.updated_ts
            """, (
                rec.recommendation_id, rec.entity_type, rec.entity_id, rec.household_id,
                rec.opportunity_id, rec.prediction_id, rec.playbook_id,
                rec.recommendation_type.value, rec.title, rec.action_text, rec.rationale,
                rec.score, rec.confidence, rec.status.value, rec.compliance_status.value,
                json.dumps(rec.supporting_documents), json.dumps(rec.evidence),
                json.dumps(rec.reasoning_steps), rec.created_ts.isoformat(),
                rec.updated_ts.isoformat()
            ))
            conn.commit()

    def update_status(self, recommendation_id: str, status: RecommendationStatus) -> None:
        with self.db.connect() as conn:
            conn.execute("""
                UPDATE phx_dm_local_recommendation
                SET status = ?, updated_ts = CURRENT_TIMESTAMP
                WHERE recommendation_id = ?
            """, (status.value, recommendation_id))
            conn.commit()

    def list_recommendations(self, entity_id: str | None = None, recommendation_type: str | None = None, status: str | None = None, limit: int = 100) -> list[dict]:
        sql = "SELECT * FROM phx_dm_local_recommendation WHERE 1=1"
        params = []
        if entity_id:
            sql += " AND entity_id = ?"
            params.append(entity_id)
        if recommendation_type:
            sql += " AND recommendation_type = ?"
            params.append(recommendation_type)
        if status:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY score DESC LIMIT ?"
        params.append(limit)
        rows = self.db.query(sql, tuple(params))
        for row in rows:
            row["supporting_documents"] = json.loads(row.pop("supporting_documents_json") or "[]")
            row["evidence"] = json.loads(row.pop("evidence_json") or "[]")
            row["reasoning_steps"] = json.loads(row.pop("reasoning_steps_json") or "[]")
        return rows

    def get_recommendation(self, recommendation_id: str) -> dict | None:
        rows = self.db.query(
            "SELECT * FROM phx_dm_local_recommendation WHERE recommendation_id = ?",
            (recommendation_id,),
        )
        if not rows:
            return None
        row = rows[0]
        row["supporting_documents"] = json.loads(row.pop("supporting_documents_json") or "[]")
        row["evidence"] = json.loads(row.pop("evidence_json") or "[]")
        row["reasoning_steps"] = json.loads(row.pop("reasoning_steps_json") or "[]")
        return row

    def counts(self) -> list[dict]:
        return self.db.query("""
            SELECT recommendation_type, status, compliance_status, COUNT(*) AS recommendation_count
            FROM phx_dm_local_recommendation
            GROUP BY recommendation_type, status, compliance_status
            ORDER BY recommendation_type, recommendation_count DESC
        """)
