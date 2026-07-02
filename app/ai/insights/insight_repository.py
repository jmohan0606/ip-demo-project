from __future__ import annotations

import json
from app.feature_store.sqlite_manager import SQLiteManager
from app.models.insights_coaching import CoachingPlan, InsightCard, InsightDashboardPayload


class InsightRepository:
    def __init__(self) -> None:
        self.db = SQLiteManager()
        self.initialize()

    def initialize(self) -> None:
        self.db.initialize_foundation_tables()
        with self.db.connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS phx_dm_local_insight_card (
                    insight_id TEXT PRIMARY KEY,
                    scope_type TEXT,
                    scope_id TEXT,
                    persona TEXT,
                    time_period TEXT,
                    card_type TEXT,
                    title TEXT,
                    summary TEXT,
                    severity TEXT,
                    confidence REAL,
                    evidence_json TEXT,
                    reasoning_steps_json TEXT,
                    recommended_actions_json TEXT,
                    created_ts TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS phx_dm_local_coaching_plan (
                    coaching_plan_id TEXT PRIMARY KEY,
                    scope_type TEXT,
                    scope_id TEXT,
                    persona TEXT,
                    tone TEXT,
                    summary TEXT,
                    focus_areas_json TEXT,
                    next_best_actions_json TEXT,
                    manager_review_notes_json TEXT,
                    advisor_talk_track_json TEXT,
                    confidence REAL,
                    created_ts TEXT
                )
            """)
            conn.commit()

    def save_payload(self, payload: InsightDashboardPayload) -> None:
        with self.db.connect() as conn:
            for card in payload.cards:
                conn.execute("""
                    INSERT INTO phx_dm_local_insight_card (
                        insight_id, scope_type, scope_id, persona, time_period, card_type,
                        title, summary, severity, confidence, evidence_json,
                        reasoning_steps_json, recommended_actions_json, created_ts
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(insight_id) DO UPDATE SET
                        summary=excluded.summary,
                        confidence=excluded.confidence
                """, (
                    card.insight_id, payload.scope_type.value, payload.scope_id, payload.persona,
                    payload.time_period, card.card_type.value, card.title, card.summary,
                    card.severity, card.confidence,
                    json.dumps([e.model_dump() for e in card.evidence]),
                    json.dumps(card.reasoning_steps),
                    json.dumps(card.recommended_actions),
                    payload.generated_at.isoformat(),
                ))
            if payload.coaching_plan:
                plan = payload.coaching_plan
                conn.execute("""
                    INSERT INTO phx_dm_local_coaching_plan (
                        coaching_plan_id, scope_type, scope_id, persona, tone, summary,
                        focus_areas_json, next_best_actions_json, manager_review_notes_json,
                        advisor_talk_track_json, confidence, created_ts
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(coaching_plan_id) DO UPDATE SET
                        summary=excluded.summary,
                        confidence=excluded.confidence
                """, (
                    plan.coaching_plan_id, plan.scope_type.value, plan.scope_id, plan.persona,
                    plan.tone.value, plan.summary, json.dumps(plan.focus_areas),
                    json.dumps(plan.next_best_actions), json.dumps(plan.manager_review_notes),
                    json.dumps(plan.advisor_talk_track), plan.confidence, plan.created_ts.isoformat(),
                ))
            conn.commit()

    def list_cards(self, scope_id: str | None = None, limit: int = 100) -> list[dict]:
        if scope_id:
            rows = self.db.query("""
                SELECT * FROM phx_dm_local_insight_card
                WHERE scope_id = ?
                ORDER BY created_ts DESC LIMIT ?
            """, (scope_id, limit))
        else:
            rows = self.db.query("""
                SELECT * FROM phx_dm_local_insight_card
                ORDER BY created_ts DESC LIMIT ?
            """, (limit,))
        for row in rows:
            row["evidence"] = json.loads(row.pop("evidence_json") or "[]")
            row["reasoning_steps"] = json.loads(row.pop("reasoning_steps_json") or "[]")
            row["recommended_actions"] = json.loads(row.pop("recommended_actions_json") or "[]")
        return rows

    def counts(self) -> list[dict]:
        return self.db.query("""
            SELECT card_type, severity, COUNT(*) AS insight_count
            FROM phx_dm_local_insight_card
            GROUP BY card_type, severity
            ORDER BY insight_count DESC
        """)
