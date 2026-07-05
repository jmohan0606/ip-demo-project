from __future__ import annotations

from app.feature_store.sqlite_manager import SQLiteManager
from app.models.feedback_learning import FeedbackEventRecord, LearningSignalRecord, OutcomeEventRecord


class FeedbackLearningRepository:
    def __init__(self) -> None:
        self.db = SQLiteManager()
        self.initialize()

    def initialize(self) -> None:
        self.db.initialize_foundation_tables()
        with self.db.connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS phx_dm_local_feedback_event (
                    feedback_id TEXT PRIMARY KEY,
                    recommendation_id TEXT,
                    actor TEXT,
                    action TEXT,
                    reason TEXT,
                    modified_action_text TEXT,
                    reward_score REAL,
                    created_ts TEXT,
                    status TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS phx_dm_local_outcome_event (
                    outcome_id TEXT PRIMARY KEY,
                    feedback_id TEXT,
                    recommendation_id TEXT,
                    outcome_type TEXT,
                    outcome_value REAL,
                    outcome_summary TEXT,
                    created_ts TEXT,
                    status TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS phx_dm_local_learning_signal (
                    learning_signal_id TEXT PRIMARY KEY,
                    feedback_id TEXT,
                    recommendation_id TEXT,
                    outcome_id TEXT,
                    signal_type TEXT,
                    signal_value REAL,
                    signal_summary TEXT,
                    ranking_weight_delta REAL,
                    memory_update_summary TEXT,
                    created_ts TEXT,
                    status TEXT
                )
            """)
            conn.commit()

    def save_feedback(self, feedback: FeedbackEventRecord) -> None:
        with self.db.connect() as conn:
            conn.execute("""
                INSERT INTO phx_dm_local_feedback_event (
                    feedback_id, recommendation_id, actor, action, reason,
                    modified_action_text, reward_score, created_ts, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(feedback_id) DO UPDATE SET
                    action=excluded.action,
                    reason=excluded.reason,
                    reward_score=excluded.reward_score
            """, (
                feedback.feedback_id, feedback.recommendation_id, feedback.actor.value,
                feedback.action.value, feedback.reason, feedback.modified_action_text,
                feedback.reward_score, feedback.created_ts.isoformat(), feedback.status
            ))
            conn.commit()

    def save_outcome(self, outcome: OutcomeEventRecord) -> None:
        with self.db.connect() as conn:
            conn.execute("""
                INSERT INTO phx_dm_local_outcome_event (
                    outcome_id, feedback_id, recommendation_id, outcome_type,
                    outcome_value, outcome_summary, created_ts, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(outcome_id) DO UPDATE SET
                    outcome_value=excluded.outcome_value,
                    outcome_summary=excluded.outcome_summary
            """, (
                outcome.outcome_id, outcome.feedback_id, outcome.recommendation_id,
                outcome.outcome_type.value, outcome.outcome_value, outcome.outcome_summary,
                outcome.created_ts.isoformat(), outcome.status
            ))
            conn.commit()

    def save_learning_signal(self, signal: LearningSignalRecord) -> None:
        with self.db.connect() as conn:
            conn.execute("""
                INSERT INTO phx_dm_local_learning_signal (
                    learning_signal_id, feedback_id, recommendation_id, outcome_id,
                    signal_type, signal_value, signal_summary, ranking_weight_delta,
                    memory_update_summary, created_ts, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(learning_signal_id) DO UPDATE SET
                    signal_value=excluded.signal_value,
                    signal_summary=excluded.signal_summary
            """, (
                signal.learning_signal_id, signal.feedback_id, signal.recommendation_id,
                signal.outcome_id, signal.signal_type.value, signal.signal_value,
                signal.signal_summary, signal.ranking_weight_delta,
                signal.memory_update_summary, signal.created_ts.isoformat(), signal.status
            ))
            conn.commit()

    def list_feedback(self, recommendation_id: str | None = None, actor: str | None = None, action: str | None = None, limit: int = 100) -> list[dict]:
        sql = "SELECT * FROM phx_dm_local_feedback_event WHERE 1=1"
        params = []
        if recommendation_id:
            sql += " AND recommendation_id = ?"
            params.append(recommendation_id)
        if actor:
            sql += " AND actor = ?"
            params.append(actor)
        if action:
            sql += " AND action = ?"
            params.append(action)
        sql += " ORDER BY created_ts DESC LIMIT ?"
        params.append(limit)
        return self.db.query(sql, tuple(params))

    def list_learning_signals(self, limit: int = 100) -> list[dict]:
        return self.db.query("""
            SELECT * FROM phx_dm_local_learning_signal
            ORDER BY created_ts DESC LIMIT ?
        """, (limit,))

    def counts(self) -> list[dict]:
        return self.db.query("""
            SELECT actor, action, COUNT(*) AS feedback_count, AVG(reward_score) AS avg_reward
            FROM phx_dm_local_feedback_event
            GROUP BY actor, action
            ORDER BY feedback_count DESC
        """)
