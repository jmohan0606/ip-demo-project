# ⚠️ LEGACY — REFERENCE ONLY. DO NOT USE FOR THE CLIENT REBUILD.

This folder is the **old 42-vertex build's** TigerGraph artifacts (schema, `queries_v1`,
`sample_data` with `ADV0001`-style IDs). It is **not loaded at runtime** and is **not** the
rebuild source.

**The single source of truth for schema, loading jobs, GQ-### queries, manifest, and seed CSVs
is `docs/tigergraph_foundation/`** (60 vertices / 132 edges / 185 loading jobs / 50 queries /
192 manifest CSVs, validator: `docs/tigergraph_foundation/scripts/validate_package.py` →
STATUS PASS).

See `TIGERGRAPH_AUDIT.md` at the repo root for the full audit (2026-07-07). This folder is kept
only because a few legacy fallback code paths (`app/feature_store/csv_loader.py`,
`app/embeddings/graph_builder.py`, `app/graph/mock/mock_graph_data_service.py`) still point at
`sample_data/`; none are on the live or rebuild path.
