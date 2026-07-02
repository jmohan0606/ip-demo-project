from pathlib import Path
import sqlite3

def test_preloaded_sqlite_exists():
    db = Path("data/sqlite/iperform.db")
    assert db.exists()
    assert db.stat().st_size > 0

def test_preloaded_sqlite_has_recommendations():
    conn = sqlite3.connect("data/sqlite/iperform.db")
    count = conn.execute("SELECT COUNT(*) FROM phx_dm_local_recommendation").fetchone()[0]
    conn.close()
    assert count > 0
