from __future__ import annotations

import json
from app.feature_store.sqlite_manager import SQLiteManager
from app.models.opportunities import OpportunityRecord


class OpportunityRepository:
    def __init__(self) -> None:
        self.db = SQLiteManager()
        self.initialize()

    def initialize(self) -> None:
        self.db.initialize_foundation_tables()
        with self.db.connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS phx_dm_local_opportunity (
                    opportunity_id TEXT PRIMARY KEY,
                    entity_type TEXT,
                    entity_id TEXT,
                    household_id TEXT,
                    opportunity_type TEXT,
                    title TEXT,
                    description TEXT,
                    score REAL,
                    priority TEXT,
                    status TEXT,
                    evidence_json TEXT,
                    reasoning_steps_json TEXT,
                    feature_snapshot_json TEXT,
                    prediction_id TEXT,
                    created_ts TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_phx_dm_opportunity_entity
                ON phx_dm_local_opportunity(entity_type, entity_id, opportunity_type, priority)
            """)
            conn.commit()

    def save_opportunity(self, opp: OpportunityRecord) -> None:
        with self.db.connect() as conn:
            conn.execute("""
                INSERT INTO phx_dm_local_opportunity (
                    opportunity_id, entity_type, entity_id, household_id, opportunity_type,
                    title, description, score, priority, status, evidence_json,
                    reasoning_steps_json, feature_snapshot_json, prediction_id, created_ts
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(opportunity_id) DO UPDATE SET
                    score=excluded.score,
                    priority=excluded.priority,
                    status=excluded.status,
                    evidence_json=excluded.evidence_json,
                    reasoning_steps_json=excluded.reasoning_steps_json
            """, (
                opp.opportunity_id, opp.entity_type, opp.entity_id, opp.household_id,
                opp.opportunity_type.value, opp.title, opp.description, opp.score,
                opp.priority.value, opp.status.value, json.dumps(opp.evidence),
                json.dumps(opp.reasoning_steps), json.dumps(opp.feature_snapshot),
                opp.prediction_id, opp.created_ts.isoformat()
            ))
            conn.commit()

    def list_opportunities(self, entity_id: str | None = None, opportunity_type: str | None = None, priority: str | None = None, limit: int = 100) -> list[dict]:
        sql = "SELECT * FROM phx_dm_local_opportunity WHERE 1=1"
        params = []
        if entity_id:
            sql += " AND entity_id = ?"
            params.append(entity_id)
        if opportunity_type:
            sql += " AND opportunity_type = ?"
            params.append(opportunity_type)
        if priority:
            sql += " AND priority = ?"
            params.append(priority)
        sql += " ORDER BY score DESC LIMIT ?"
        params.append(limit)
        rows = self.db.query(sql, tuple(params))
        for row in rows:
            row["evidence"] = json.loads(row.pop("evidence_json") or "[]")
            row["reasoning_steps"] = json.loads(row.pop("reasoning_steps_json") or "[]")
            row["feature_snapshot"] = json.loads(row.pop("feature_snapshot_json") or "{}")
        return rows

    def counts(self) -> list[dict]:
        return self.db.query("""
            SELECT opportunity_type, priority, COUNT(*) AS opportunity_count
            FROM phx_dm_local_opportunity
            GROUP BY opportunity_type, priority
            ORDER BY opportunity_type, opportunity_count DESC
        """)
