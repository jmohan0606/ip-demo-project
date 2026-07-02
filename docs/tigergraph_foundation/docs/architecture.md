# Story 1 Architecture

## Component flow

```text
React/TypeScript + Material UI
Data Management and Validation Console
                  |
                  | HTTPS / JSON
                  v
FastAPI
- catalog APIs
- CSV preflight validation
- dependency resolution
- ingestion orchestration
- graph/query validation
                  |
        +---------+----------+
        |                    |
        v                    v
SQLite tracker          TigerGraph RESTPP
- ingestion_run         - vertex/edge upserts
- ingestion_file        - installed queries
- ingestion_batch       - cardinality built-ins
- ingestion_row_error
- ingestion_checkpoint
- source_file_version
- graph_validation_result
        ^                    ^
        |                    |
        +-- manifest + CSV --+
```

## Core decisions

1. React never calls TigerGraph directly and never receives graph credentials.
2. FastAPI is the only application integration boundary for RESTPP.
3. TigerGraph is the business-data system of record.
4. SQLite is limited to local operational metadata for ingestion and validation.
5. `data/manifest.json` is the authoritative source-to-graph mapping and load order.
6. Every CSV target has a corresponding schema target and server-side fallback loading job.
7. Edge upserts use `vertex_must_exist=true` so missing endpoints fail instead of silently creating incomplete graph structures.
8. File and row processing are deterministic and resumable.
9. Mock mode is an explicit local test mode and is visibly identified in the UI.
10. GSQL query contracts and response objects are intended to be consumed by Story 2 business pages and Story 3 agentic workflows.

## Load lifecycle

1. Discover the manifest and CSV package.
2. Validate files, headers, mappings, row counts, key fields and dependencies.
3. Select targets or include all dependencies.
4. Create a tracked ingestion run in SQLite.
5. Process vertices before dependent edges in manifest order.
6. Construct RESTPP upsert payloads from explicit source-column mappings.
7. Submit configurable batches.
8. Require exact accepted counts.
9. Isolate failed batches recursively to identify row errors.
10. Persist progress/checkpoints and enable pause/resume/retry.
11. Validate TigerGraph counts and execute installed query test cases.

## Data consumption after Story 1

The graph is designed to be the single shared sample-data source for later application work. Revenue pages, persona dashboards, Advisor 360, AGP, CRM, feature engineering, embeddings, predictions, opportunities, recommendations, memory and explainability screens must consume TigerGraph APIs/queries rather than separate UI-only fixtures.
