from __future__ import annotations
import sqlite3
from pathlib import Path
from app.config.settings import get_settings


class SQLiteManager:
    def __init__(self, db_path: str | None = None) -> None:
        settings = get_settings()
        self.db_path = Path(db_path or settings.sqlite_db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize_foundation_tables(self) -> None:
        statements = [
            '''CREATE TABLE IF NOT EXISTS phx_dm_runtime_metadata (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )''',
            '''CREATE TABLE IF NOT EXISTS phx_dm_upload_checkpoint (
                checkpoint_id TEXT PRIMARY KEY,
                entity_name TEXT NOT NULL,
                file_name TEXT NOT NULL,
                batch_id TEXT NOT NULL,
                last_processed_row INTEGER DEFAULT 0,
                status TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )''',
            '''CREATE TABLE IF NOT EXISTS phx_dm_feature_registry (
                feature_name TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                description TEXT,
                version TEXT DEFAULT '1.0',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )''',
        ]
        with self.connect() as conn:
            for statement in statements:
                conn.execute(statement)
            conn.commit()


    def query(self, sql: str, params: tuple = ()) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(row) for row in rows]

    def execute(self, sql: str, params: tuple = ()) -> None:
        with self.connect() as conn:
            conn.execute(sql, params)
            conn.commit()

    def execute_many(self, sql: str, params_list: list[tuple]) -> None:
        with self.connect() as conn:
            conn.executemany(sql, params_list)
            conn.commit()
