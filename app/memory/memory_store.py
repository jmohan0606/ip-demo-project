from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.memory.models import MemoryEvent


class SQLiteMemoryStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_events (
                memory_id TEXT PRIMARY KEY,
                memory_type TEXT NOT NULL,
                scope_id TEXT NOT NULL,
                persona TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                importance REAL NOT NULL,
                tags_json TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS context_packets (
                context_id TEXT PRIMARY KEY,
                scope_id TEXT NOT NULL,
                persona TEXT NOT NULL,
                packet_json TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """)
            conn.commit()

    def upsert_memory(self, memory: MemoryEvent) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO memory_events(
                    memory_id, memory_type, scope_id, persona, title, content, importance, tags_json, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memory.memory_id,
                    memory.memory_type,
                    memory.scope_id,
                    memory.persona,
                    memory.title,
                    memory.content,
                    memory.importance,
                    json.dumps(memory.tags),
                    json.dumps(memory.metadata),
                ),
            )
            conn.commit()

    def search_memory(self, scope_id: str, persona: str, query: str = "", limit: int = 10) -> list[dict[str, Any]]:
        terms = [term.lower() for term in query.split() if term.strip()]
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT memory_id, memory_type, scope_id, persona, title, content, importance, tags_json, metadata_json, created_at
                FROM memory_events
                WHERE scope_id=? OR persona=? OR persona='Global'
                ORDER BY importance DESC, created_at DESC
                LIMIT 100
                """,
                (scope_id, persona),
            ).fetchall()

        results = []
        for row in rows:
            text = f"{row[4]} {row[5]}".lower()
            score = float(row[6])
            if terms:
                score += sum(0.1 for term in terms if term in text)
            results.append({
                "memory_id": row[0],
                "memory_type": row[1],
                "scope_id": row[2],
                "persona": row[3],
                "title": row[4],
                "content": row[5],
                "importance": row[6],
                "tags": json.loads(row[7]),
                "metadata": json.loads(row[8]),
                "created_at": row[9],
                "retrieval_score": round(score, 4),
            })
        results.sort(key=lambda item: item["retrieval_score"], reverse=True)
        return results[:limit]

    def save_context_packet(self, packet: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO context_packets(context_id, scope_id, persona, packet_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    packet["context_id"],
                    packet["scope_id"],
                    packet["persona"],
                    json.dumps(packet),
                ),
            )
            conn.commit()

    def count(self) -> dict[str, int]:
        with self._connect() as conn:
            memories = conn.execute("SELECT COUNT(*) FROM memory_events").fetchone()[0]
            packets = conn.execute("SELECT COUNT(*) FROM context_packets").fetchone()[0]
        return {"memory_events": int(memories), "context_packets": int(packets)}
