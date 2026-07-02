from __future__ import annotations

import json
from app.feature_store.sqlite_manager import SQLiteManager
from app.models.embeddings import NodeEmbedding, SimilarityMatch


class EmbeddingRepository:
    def __init__(self) -> None:
        self.db = SQLiteManager()
        self.initialize()

    def initialize(self) -> None:
        self.db.initialize_foundation_tables()
        with self.db.connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS phx_dm_local_embedding (
                    embedding_id TEXT PRIMARY KEY,
                    entity_type TEXT,
                    entity_id TEXT,
                    embedding_type TEXT,
                    model_name TEXT,
                    vector_json TEXT,
                    vector_preview TEXT,
                    created_ts TEXT,
                    status TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_phx_dm_local_embedding_entity
                ON phx_dm_local_embedding(entity_type, entity_id)
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS phx_dm_local_similarity_match (
                    similarity_id TEXT PRIMARY KEY,
                    source_entity_type TEXT,
                    source_entity_id TEXT,
                    target_entity_type TEXT,
                    target_entity_id TEXT,
                    similarity_type TEXT,
                    similarity_score REAL,
                    explanation TEXT,
                    created_ts TEXT
                )
            """)
            conn.commit()

    def save_embedding(self, emb: NodeEmbedding) -> None:
        with self.db.connect() as conn:
            conn.execute("""
                INSERT INTO phx_dm_local_embedding (
                    embedding_id, entity_type, entity_id, embedding_type, model_name,
                    vector_json, vector_preview, created_ts, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(embedding_id) DO UPDATE SET
                    vector_json=excluded.vector_json,
                    vector_preview=excluded.vector_preview,
                    created_ts=excluded.created_ts
            """, (
                emb.embedding_id, emb.entity_type.value, emb.entity_id, emb.embedding_type.value,
                emb.model_name, json.dumps(emb.vector), emb.vector_preview,
                emb.created_ts.isoformat(), emb.status
            ))
            conn.commit()

    def save_similarity(self, match: SimilarityMatch) -> None:
        with self.db.connect() as conn:
            conn.execute("""
                INSERT INTO phx_dm_local_similarity_match (
                    similarity_id, source_entity_type, source_entity_id, target_entity_type,
                    target_entity_id, similarity_type, similarity_score, explanation, created_ts
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(similarity_id) DO UPDATE SET
                    similarity_score=excluded.similarity_score,
                    explanation=excluded.explanation
            """, (
                match.similarity_id, match.source_entity_type.value, match.source_entity_id,
                match.target_entity_type.value, match.target_entity_id, match.similarity_type.value,
                match.similarity_score, match.explanation, match.created_ts.isoformat()
            ))
            conn.commit()

    def list_embeddings(self, entity_type: str | None = None, limit: int = 100) -> list[dict]:
        if entity_type:
            rows = self.db.query("""
                SELECT * FROM phx_dm_local_embedding
                WHERE entity_type = ?
                ORDER BY created_ts DESC LIMIT ?
            """, (entity_type, limit))
        else:
            rows = self.db.query("""
                SELECT * FROM phx_dm_local_embedding
                ORDER BY created_ts DESC LIMIT ?
            """, (limit,))
        for row in rows:
            row["vector"] = json.loads(row.pop("vector_json"))
        return rows

    def list_similarity(self, entity_type: str | None = None, entity_id: str | None = None, limit: int = 100) -> list[dict]:
        if entity_type and entity_id:
            return self.db.query("""
                SELECT * FROM phx_dm_local_similarity_match
                WHERE source_entity_type = ? AND source_entity_id = ?
                ORDER BY similarity_score DESC LIMIT ?
            """, (entity_type, entity_id, limit))
        return self.db.query("""
            SELECT * FROM phx_dm_local_similarity_match
            ORDER BY similarity_score DESC LIMIT ?
        """, (limit,))

    def counts(self) -> list[dict]:
        return self.db.query("""
            SELECT entity_type, COUNT(*) AS embedding_count
            FROM phx_dm_local_embedding
            GROUP BY entity_type
            ORDER BY embedding_count DESC
        """)
