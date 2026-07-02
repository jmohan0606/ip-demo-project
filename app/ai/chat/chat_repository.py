from __future__ import annotations

import json
from app.feature_store.sqlite_manager import SQLiteManager
from app.models.ai_chat import ChatResponse


class ChatRepository:
    def __init__(self) -> None:
        self.db = SQLiteManager()
        self.initialize()

    def initialize(self) -> None:
        self.db.initialize_foundation_tables()
        with self.db.connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS phx_dm_local_chat_turn (
                    conversation_turn_id TEXT PRIMARY KEY,
                    conversation_id TEXT,
                    question TEXT,
                    answer TEXT,
                    persona TEXT,
                    scope_type TEXT,
                    scope_id TEXT,
                    context_items_json TEXT,
                    reasoning_steps_json TEXT,
                    confidence REAL,
                    generated_at TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_phx_dm_chat_conversation
                ON phx_dm_local_chat_turn(conversation_id, generated_at)
            """)
            conn.commit()

    def save_response(self, response: ChatResponse) -> None:
        with self.db.connect() as conn:
            conn.execute("""
                INSERT INTO phx_dm_local_chat_turn (
                    conversation_turn_id, conversation_id, question, answer, persona,
                    scope_type, scope_id, context_items_json, reasoning_steps_json,
                    confidence, generated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(conversation_turn_id) DO UPDATE SET
                    answer=excluded.answer,
                    context_items_json=excluded.context_items_json
            """, (
                response.conversation_turn_id,
                response.conversation_id,
                "",
                response.answer,
                response.persona.value,
                response.scope_type.value,
                response.scope_id,
                json.dumps([c.model_dump() for c in response.context_items]),
                json.dumps(response.reasoning_steps),
                response.confidence,
                response.generated_at.isoformat(),
            ))
            conn.commit()

    def save_turn(self, response: ChatResponse, question: str) -> None:
        with self.db.connect() as conn:
            conn.execute("""
                INSERT INTO phx_dm_local_chat_turn (
                    conversation_turn_id, conversation_id, question, answer, persona,
                    scope_type, scope_id, context_items_json, reasoning_steps_json,
                    confidence, generated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                response.conversation_turn_id,
                response.conversation_id,
                question,
                response.answer,
                response.persona.value,
                response.scope_type.value,
                response.scope_id,
                json.dumps([c.model_dump() for c in response.context_items]),
                json.dumps(response.reasoning_steps),
                response.confidence,
                response.generated_at.isoformat(),
            ))
            conn.commit()

    def history(self, conversation_id: str | None = None, scope_id: str | None = None, limit: int = 50) -> list[dict]:
        sql = "SELECT * FROM phx_dm_local_chat_turn WHERE 1=1"
        params = []
        if conversation_id:
            sql += " AND conversation_id = ?"
            params.append(conversation_id)
        if scope_id:
            sql += " AND scope_id = ?"
            params.append(scope_id)
        sql += " ORDER BY generated_at DESC LIMIT ?"
        params.append(limit)
        rows = self.db.query(sql, tuple(params))
        for row in rows:
            row["context_items"] = json.loads(row.pop("context_items_json") or "[]")
            row["reasoning_steps"] = json.loads(row.pop("reasoning_steps_json") or "[]")
        return rows
