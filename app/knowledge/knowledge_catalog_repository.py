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

    def find_document(self, document_name: str, content_hash: str) -> KnowledgeDocument | None:
        """Return the already-indexed document matching name + content sha256, if any
        (ingestion idempotency). Rows indexed before hashes were recorded match on
        name alone — the sample corpus is keyed by unique file names."""
        rows = self.db.query(
            "SELECT * FROM phx_dm_knowledge_document_catalog WHERE document_name = ? ORDER BY uploaded_at ASC",
            (document_name,),
        )
        for row in rows:
            meta = json.loads(row.get("metadata_json") or "{}")
            stored_hash = meta.get("content_hash")
            if stored_hash is None or stored_hash == content_hash:
                return KnowledgeDocument(
                    document_id=row["document_id"], document_name=row["document_name"],
                    document_type=row.get("document_type") or "Other",
                    document_category=row.get("document_category") or "General",
                    source_path=row.get("source_path") or "", version=row.get("version") or "1.0",
                    status=row.get("status") or "indexed",
                )
        return None

    def chunk_ids_for_document(self, document_id: str) -> list[str]:
        return [r["chunk_id"] for r in self.db.query(
            "SELECT chunk_id FROM phx_dm_knowledge_chunk_catalog WHERE document_id = ?", (document_id,))]

    def delete_document(self, document_id: str) -> None:
        with self.db.connect() as conn:
            conn.execute("DELETE FROM phx_dm_knowledge_chunk_catalog WHERE document_id = ?", (document_id,))
            conn.execute("DELETE FROM phx_dm_knowledge_document_catalog WHERE document_id = ?", (document_id,))
            conn.commit()
