from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class LearningStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS recommendation_feedback (
                feedback_id TEXT PRIMARY KEY,
                recommendation_id TEXT NOT NULL,
                action TEXT NOT NULL,
                notes TEXT,
                learning_signal TEXT,
                score_delta REAL,
                memory_update TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS recommendation_state (
                recommendation_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                score_adjustment REAL DEFAULT 0,
                last_action TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """)
            conn.commit()

    def save_feedback(self, feedback: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO recommendation_feedback(
                    feedback_id, recommendation_id, action, notes, learning_signal, score_delta, memory_update
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    feedback["feedback_id"],
                    feedback["recommendation_id"],
                    feedback["action"],
                    feedback.get("notes", ""),
                    feedback.get("learning_signal", ""),
                    feedback.get("score_delta", 0),
                    feedback.get("memory_update", ""),
                ),
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO recommendation_state(
                    recommendation_id, status, score_adjustment, last_action
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    feedback["recommendation_id"],
                    feedback["action"],
                    feedback.get("score_delta", 0),
                    feedback["action"],
                ),
            )
            conn.commit()

    def get_state(self, recommendation_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT recommendation_id, status, score_adjustment, last_action FROM recommendation_state WHERE recommendation_id=?",
                (recommendation_id,),
            ).fetchone()
        if not row:
            return None
        return {"recommendation_id": row[0], "status": row[1], "score_adjustment": row[2], "last_action": row[3]}

    def count(self) -> dict[str, int]:
        with self._connect() as conn:
            feedback = conn.execute("SELECT COUNT(*) FROM recommendation_feedback").fetchone()[0]
            state = conn.execute("SELECT COUNT(*) FROM recommendation_state").fetchone()[0]
        return {"feedback_events": int(feedback), "recommendation_states": int(state)}
