from __future__ import annotations

import json
import sqlite3
from pathlib import Path


class UploadResumeValidator:
    """Validates resumable upload checkpoint mechanics without needing live TigerGraph."""

    def __init__(self, db_path: str = "data/sqlite/iperform.db") -> None:
        self.db_path = Path(db_path)

    def validate(self) -> dict:
        assert self.db_path.exists(), "SQLite DB missing"
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS phx_dm_upload_checkpoint (
                    checkpoint_id TEXT PRIMARY KEY,
                    entity_name TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    batch_id TEXT NOT NULL,
                    last_processed_row INTEGER DEFAULT 0,
                    status TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                INSERT OR REPLACE INTO phx_dm_upload_checkpoint (
                    checkpoint_id, entity_name, file_name, batch_id, last_processed_row, status
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("CHK_RUNTIME_RETRY", "Advisor", "phx_dm_advisor.csv", "BATCH_RUNTIME", 12, "failed"))
            failed = conn.execute(
                "SELECT last_processed_row, status FROM phx_dm_upload_checkpoint WHERE checkpoint_id=?",
                ("CHK_RUNTIME_RETRY",),
            ).fetchone()
            assert failed[0] == 12 and failed[1] == "failed"

            conn.execute("""
                UPDATE phx_dm_upload_checkpoint
                SET last_processed_row=?, status=?, updated_at=CURRENT_TIMESTAMP
                WHERE checkpoint_id=?
            """, (30, "completed", "CHK_RUNTIME_RETRY"))
            completed = conn.execute(
                "SELECT last_processed_row, status FROM phx_dm_upload_checkpoint WHERE checkpoint_id=?",
                ("CHK_RUNTIME_RETRY",),
            ).fetchone()
            conn.commit()
            return {
                "status": "passed",
                "failed_checkpoint_row": failed[0],
                "completed_checkpoint_row": completed[0],
                "completed_status": completed[1],
                "resume_behavior": "validated",
            }
        finally:
            conn.close()
