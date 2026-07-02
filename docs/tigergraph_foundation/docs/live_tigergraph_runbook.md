# Live TigerGraph 4.2.2 Installation and Validation Runbook

This runbook is the mandatory external acceptance gate for Story 1.

## 1. Prerequisites

- TigerGraph 4.2.2 environment and authorized GSQL access.
- RESTPP host/port reachable from the FastAPI machine.
- A token permitted to upsert the graph and execute installed queries.
- A new/empty graph name or an approved migration plan for an existing graph.
- Backup/change approval before schema installation.

## 2. Review before installation

Compare any existing deployed schema with:

- `tigergraph/schema/01_vertices.gsql`
- `tigergraph/schema/02_edges.gsql`
- `tigergraph/schema/03_create_graph.gsql`
- `tigergraph/schema/schema_catalog.json`

Do not apply this package blindly to an existing graph. The package is the new consolidated Story 1 baseline because the historical source files were unavailable during rebuild.

## 3. Run local validation

```bash
make validate
```

Proceed only when the local suite passes.

## 4. Install schema, jobs and queries

Configure the GSQL command if required:

```bash
export GSQL_CMD=gsql
make live-install
```

The script runs:

1. `tigergraph/schema/00_install_schema.gsql`
2. `tigergraph/loading/install_all_loading_jobs.gsql`
3. `tigergraph/queries/install_all_queries.gsql`

Capture the complete GSQL console output. A compiler error blocks the release and must be corrected in the source file; do not bypass a failed query.

## 5. Configure FastAPI for live mode

```bash
cd backend
cp .env.example .env
```

Set:

```dotenv
MOCK_TIGERGRAPH=false
GRAPH_NAME=iperform_insights_coaching_demo
TIGERGRAPH_RESTPP_URL=https://<host>:14240/restpp
TIGERGRAPH_TOKEN=<token>
TIGERGRAPH_VERIFY_SSL=true
TRACKER_DB_PATH=../runtime/ingestion_tracker.db
LOAD_BATCH_SIZE=500
```

Use `TIGERGRAPH_VERIFY_SSL=false` only for a controlled nonproduction certificate scenario and document the exception.

## 6. Start backend and frontend

```bash
# terminal 1
cd backend
uvicorn app.main:app --reload --port 8000

# terminal 2
cd frontend
npm run dev
```

Confirm the UI reports **live** mode and RESTPP health before loading.

## 7. Preflight and load

From the UI:

1. Select **Validate All**.
2. Confirm 182 targets, no mapping errors and expected dependency order.
3. Start **Load All in Dependency Order**.
4. Watch run/file/batch progress.
5. Stop and investigate any accepted-count mismatch or row error.
6. Use retry only after correcting the source/mapping/data issue.

The loader submits `POST /restpp/graph/iperform_insights_coaching_demo`. Edges use `vertex_must_exist=true`.

## 8. Run live validation

```bash
export TIGERGRAPH_RESTPP_URL=https://<host>:14240/restpp
export TIGERGRAPH_TOKEN=<token>
make live-validate
```

The validator checks:

- RESTPP echo.
- Exact expected cardinality for every vertex and edge target.
- All 43 installed query cases.
- RESTPP error responses and elapsed times.

Review:

- `reports/live_tigergraph_validation.json`
- `reports/live_tigergraph_validation.md`

## 9. Acceptance criteria

Story 1 live validation passes only when:

- Schema, all loading jobs and all 43 queries install without error.
- All 182 files complete with zero unresolved row failures.
- Cardinality equals manifest expected counts for every target.
- All 43 query cases return without TigerGraph error.
- Representative business outputs are manually reviewed for hierarchy, revenue, AGP, CRM, AI lineage, memory and feedback semantics.

## 10. Failure handling

- **Compiler error:** correct the GSQL source and rerun the affected install step.
- **Accepted-count mismatch:** inspect RESTPP response and SQLite row errors; do not mark the file complete.
- **Missing edge endpoint:** verify dependency order and source vertex IDs.
- **Cardinality mismatch:** compare manifest expected count, SQLite run history and TigerGraph built-in counts.
- **Query result logically wrong:** correct traversal/filter/aggregation logic and add or improve the deterministic test case.
- **Network/token error:** validate RESTPP URL, token permissions, TLS and firewall path.
