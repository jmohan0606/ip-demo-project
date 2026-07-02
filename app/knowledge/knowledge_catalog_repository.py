from __future__ import annotations

import json
from app.feature_store.sqlite_manager import SQLiteManager
from app.models.knowledge import KnowledgeDocument


class KnowledgeCatalogRepository:
    def __init__(self) -> None:
        self.db = SQLiteManager()
        self.initialize()

    def initialize(self) -> None:
        self.db.initialize_foundation_tables()
        with self.db.connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS phx_dm_knowledge_document_catalog (
                    document_id TEXT PRIMARY KEY,
                    document_name TEXT NOT NULL,
                    document_type TEXT,
                    document_category TEXT,
                    source_path TEXT,
                    version TEXT,
                    status TEXT,
                    uploaded_at TEXT,
                    metadata_json TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS phx_dm_knowledge_chunk_catalog (
                    chunk_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    chunk_index INTEGER,
                    chunk_summary TEXT,
                    metadata_json TEXT
                )
            """)
            conn.commit()

    def save_document(self, document: KnowledgeDocument, metadata: dict | None = None) -> None:
        with self.db.connect() as conn:
            conn.execute("""
                INSERT INTO phx_dm_knowledge_document_catalog (
                    document_id, document_name, document_type, document_category,
                    source_path, version, status, uploaded_at, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(document_id) DO UPDATE SET
                    status=excluded.status,
                    metadata_json=excluded.metadata_json
            """, (
                document.document_id, document.document_name, document.document_type.value,
                document.document_category, document.source_path, document.version,
                document.status.value, document.uploaded_at.isoformat(), json.dumps(metadata or {})
            ))
            conn.commit()

    def save_chunk(self, chunk_id: str, document_id: str, chunk_index: int, summary: str | None, metadata: dict | None = None) -> None:
        with self.db.connect() as conn:
            conn.execute("""
                INSERT INTO phx_dm_knowledge_chunk_catalog (
                    chunk_id, document_id, chunk_index, chunk_summary, metadata_json
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(chunk_id) DO UPDATE SET
                    chunk_summary=excluded.chunk_summary,
                    metadata_json=excluded.metadata_json
            """, (chunk_id, document_id, chunk_index, summary, json.dumps(metadata or {})))
            conn.commit()

    def list_documents(self) -> list[dict]:
        return self.db.query("SELECT * FROM phx_dm_knowledge_document_catalog ORDER BY uploaded_at DESC")
