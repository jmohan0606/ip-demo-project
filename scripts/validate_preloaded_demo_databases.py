from __future__ import annotations

import json
import sqlite3
from pathlib import Path


def main() -> None:
    db = Path("data/sqlite/iperform.db")
    chroma = Path("data/chroma")
    manifest = Path("data/preloaded/preloaded_demo_database_manifest.json")

    assert db.exists(), "Missing data/sqlite/iperform.db"
    assert db.stat().st_size > 0, "SQLite DB is empty"
    assert chroma.exists(), "Missing data/chroma"
    assert manifest.exists(), "Missing preloaded manifest"

    conn = sqlite3.connect(db)
    required = [
        "phx_dm_feature_vector",
        "phx_dm_local_prediction_result",
        "phx_dm_local_opportunity",
        "phx_dm_local_recommendation",
        "phx_dm_local_context_memory",
        "phx_dm_knowledge_document_catalog",
    ]
    counts = {}
    for table in required:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        counts[table] = count
        assert count > 0, f"{table} has no rows"
    conn.close()

    data = json.loads(manifest.read_text())
    assert data["sqlite_exists"] is True
    assert data["chroma_exists"] is True

    print("Preloaded Demo Databases validation passed.")
    print(json.dumps(counts, indent=2))
    print("Chroma path:", chroma)


if __name__ == "__main__":
    main()
