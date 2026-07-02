from __future__ import annotations
import json
from datetime import datetime
from app.feature_store.sqlite_manager import SQLiteManager
from app.models.memory import ContextMemory, MemoryScopeType, MemoryType, ConversationTurn, ReasoningTrace

class MemoryRepository:
    def __init__(self) -> None:
        self.db = SQLiteManager()
        self.initialize()

    def initialize(self) -> None:
        self.db.initialize_foundation_tables()
        with self.db.connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS phx_dm_local_context_memory (
                    memory_id TEXT PRIMARY KEY,
                    memory_type TEXT,
                    scope_type TEXT,
                    scope_id TEXT,
                    title TEXT,
                    summary TEXT,
                    facts_json TEXT,
                    confidence REAL,
                    source TEXT,
                    valid_from TEXT,
                    valid_to TEXT,
                    created_ts TEXT,
                    status TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_phx_dm_memory_scope ON phx_dm_local_context_memory(scope_type, scope_id, memory_type)")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS phx_dm_local_conversation_turn (
                    conversation_turn_id TEXT PRIMARY KEY,
                    conversation_id TEXT,
                    turn_ts TEXT,
                    user_question TEXT,
                    assistant_answer TEXT,
                    persona TEXT,
                    scope_type TEXT,
                    scope_id TEXT,
                    status TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS phx_dm_local_reasoning_trace (
                    trace_id TEXT PRIMARY KEY,
                    trace_type TEXT,
                    conclusion TEXT,
                    confidence REAL,
                    reasoning_steps_json TEXT,
                    evidence_json TEXT,
                    created_ts TEXT,
                    status TEXT
                )
            """)
            conn.commit()

    def save_memory(self, memory: ContextMemory) -> None:
        with self.db.connect() as conn:
            conn.execute("""
                INSERT INTO phx_dm_local_context_memory (
                    memory_id, memory_type, scope_type, scope_id, title, summary,
                    facts_json, confidence, source, valid_from, valid_to, created_ts, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(memory_id) DO UPDATE SET
                    summary=excluded.summary,
                    facts_json=excluded.facts_json,
                    confidence=excluded.confidence,
                    status=excluded.status
            """, (
                memory.memory_id, memory.memory_type.value, memory.scope_type.value,
                memory.scope_id, memory.title, memory.summary, json.dumps(memory.facts),
                memory.confidence, memory.source, memory.valid_from.isoformat(),
                memory.valid_to.isoformat() if memory.valid_to else None,
                memory.created_ts.isoformat(), memory.status
            ))
            conn.commit()

    def retrieve_memories(self, scope_type: MemoryScopeType, scope_id: str, memory_types: list[MemoryType] | None = None, limit: int = 10, include_expired: bool = False) -> list[ContextMemory]:
        params = [scope_type.value, scope_id]
        sql = "SELECT * FROM phx_dm_local_context_memory WHERE scope_type = ? AND scope_id = ?"
        if memory_types:
            placeholders = ",".join("?" for _ in memory_types)
            sql += f" AND memory_type IN ({placeholders})"
            params.extend([m.value for m in memory_types])
        if not include_expired:
            sql += " AND status = 'Active'"
        sql += " ORDER BY created_ts DESC LIMIT ?"
        params.append(limit)
        rows = self.db.query(sql, tuple(params))
        return [
            ContextMemory(
                memory_id=r["memory_id"],
                memory_type=MemoryType(r["memory_type"]),
                scope_type=MemoryScopeType(r["scope_type"]),
                scope_id=r["scope_id"],
                title=r["title"],
                summary=r["summary"],
                facts=json.loads(r["facts_json"] or "{}"),
                confidence=r["confidence"],
                source=r["source"],
                valid_from=datetime.fromisoformat(r["valid_from"]),
                valid_to=datetime.fromisoformat(r["valid_to"]) if r["valid_to"] else None,
                created_ts=datetime.fromisoformat(r["created_ts"]),
                status=r["status"],
            )
            for r in rows
        ]

    def save_conversation_turn(self, turn: ConversationTurn) -> None:
        with self.db.connect() as conn:
            conn.execute("""
                INSERT INTO phx_dm_local_conversation_turn (
                    conversation_turn_id, conversation_id, turn_ts, user_question,
                    assistant_answer, persona, scope_type, scope_id, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                turn.conversation_turn_id, turn.conversation_id, turn.turn_ts.isoformat(),
                turn.user_question, turn.assistant_answer, turn.persona,
                turn.scope_type.value, turn.scope_id, turn.status
            ))
            conn.commit()

    def save_reasoning_trace(self, trace: ReasoningTrace) -> None:
        with self.db.connect() as conn:
            conn.execute("""
                INSERT INTO phx_dm_local_reasoning_trace (
                    trace_id, trace_type, conclusion, confidence,
                    reasoning_steps_json, evidence_json, created_ts, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trace.trace_id, trace.trace_type, trace.conclusion, trace.confidence,
                json.dumps(trace.reasoning_steps), json.dumps(trace.evidence),
                trace.created_ts.isoformat(), trace.status
            ))
            conn.commit()

    def memory_counts_by_type(self) -> list[dict]:
        return self.db.query("""
            SELECT memory_type, COUNT(*) AS memory_count
            FROM phx_dm_local_context_memory
            GROUP BY memory_type
            ORDER BY memory_count DESC
        """)
