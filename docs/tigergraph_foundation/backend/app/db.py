from __future__ import annotations
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from .config import settings

_lock = threading.RLock()

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS ingestion_run (
  run_id TEXT PRIMARY KEY, status TEXT NOT NULL, mode TEXT NOT NULL,
  started_at TEXT NOT NULL, completed_at TEXT, total_files INTEGER DEFAULT 0,
  completed_files INTEGER DEFAULT 0, total_rows INTEGER DEFAULT 0,
  processed_rows INTEGER DEFAULT 0, succeeded_rows INTEGER DEFAULT 0,
  failed_rows INTEGER DEFAULT 0, skipped_rows INTEGER DEFAULT 0,
  retry_of_run_id TEXT, config_json TEXT, message TEXT
);
CREATE TABLE IF NOT EXISTS ingestion_file (
  run_id TEXT NOT NULL, file_path TEXT NOT NULL, target TEXT NOT NULL, kind TEXT NOT NULL,
  file_hash TEXT, status TEXT NOT NULL, total_rows INTEGER DEFAULT 0,
  processed_rows INTEGER DEFAULT 0, succeeded_rows INTEGER DEFAULT 0,
  failed_rows INTEGER DEFAULT 0, skipped_rows INTEGER DEFAULT 0,
  last_successful_batch INTEGER DEFAULT -1, next_row_number INTEGER DEFAULT 1,
  started_at TEXT, completed_at TEXT, message TEXT,
  PRIMARY KEY (run_id, file_path)
);
CREATE TABLE IF NOT EXISTS ingestion_batch (
  run_id TEXT NOT NULL, file_path TEXT NOT NULL, batch_no INTEGER NOT NULL,
  row_start INTEGER, row_end INTEGER, status TEXT NOT NULL,
  requested_rows INTEGER DEFAULT 0, succeeded_rows INTEGER DEFAULT 0, failed_rows INTEGER DEFAULT 0,
  started_at TEXT, completed_at TEXT, response_json TEXT,
  PRIMARY KEY (run_id, file_path, batch_no)
);
CREATE TABLE IF NOT EXISTS ingestion_row_error (
  error_id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL, file_path TEXT NOT NULL,
  batch_no INTEGER, row_no INTEGER, business_key TEXT, error_code TEXT,
  error_message TEXT, row_json TEXT, created_at TEXT NOT NULL, resolved INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS source_file_version (
  file_path TEXT PRIMARY KEY, file_hash TEXT NOT NULL, last_successful_run_id TEXT,
  last_loaded_at TEXT, row_count INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS graph_validation_result (
  validation_id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, rule_id TEXT,
  domain TEXT, severity TEXT, status TEXT, expected_value TEXT, actual_value TEXT,
  message TEXT, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_ingestion_run_status ON ingestion_run(status);
CREATE INDEX IF NOT EXISTS ix_ingestion_file_status ON ingestion_file(run_id,status);
CREATE INDEX IF NOT EXISTS ix_ingestion_error_run ON ingestion_row_error(run_id,resolved);
"""

def initialize_db() -> None:
    path = Path(settings.tracker_db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA)
        # Idempotent migrations for databases created by v0.1.0.
        columns = {r[1] for r in conn.execute("PRAGMA table_info(ingestion_run)")}
        for name, ddl in [("retry_of_run_id","TEXT"),("config_json","TEXT")]:
            if name not in columns: conn.execute(f"ALTER TABLE ingestion_run ADD COLUMN {name} {ddl}")
        columns = {r[1] for r in conn.execute("PRAGMA table_info(ingestion_file)")}
        if "next_row_number" not in columns: conn.execute("ALTER TABLE ingestion_file ADD COLUMN next_row_number INTEGER DEFAULT 1")
        columns = {r[1] for r in conn.execute("PRAGMA table_info(ingestion_batch)")}
        if "requested_rows" not in columns: conn.execute("ALTER TABLE ingestion_batch ADD COLUMN requested_rows INTEGER DEFAULT 0")
        columns = {r[1] for r in conn.execute("PRAGMA table_info(ingestion_row_error)")}
        if "resolved" not in columns: conn.execute("ALTER TABLE ingestion_row_error ADD COLUMN resolved INTEGER DEFAULT 0")
        conn.commit()

@contextmanager
def connection():
    initialize_db()
    with _lock:
        conn = sqlite3.connect(settings.tracker_db_path, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

def rows(query: str, params: tuple = ()) -> list[dict]:
    with connection() as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]

def row(query: str, params: tuple = ()) -> dict | None:
    values = rows(query, params)
    return values[0] if values else None

def execute(query: str, params: tuple = ()) -> None:
    with connection() as conn:
        conn.execute(query, params)

def execute_many(query: str, values: list[tuple]) -> None:
    with connection() as conn:
        conn.executemany(query, values)
