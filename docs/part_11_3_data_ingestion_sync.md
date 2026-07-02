# Part 11.3 — Data Ingestion & Synchronization Package

## Added

- Entity registry for core demo CSVs
- CSV validation framework
- Delta detection using row hash
- SQLite checkpoint tracking
- Ingestion batch history
- Error tracking
- Resume failed/incomplete upload
- MCP-first / REST fallback / local mock upsert client
- API endpoints
- Streamlit Data Ingestion & Sync page foundation

## API

```text
GET  /ingestion/entities
GET  /ingestion/batches
POST /ingestion/run
```

## Example Request

```json
{
  "entity_name": "advisor",
  "resume": true,
  "dry_run": true,
  "batch_size": 500
}
```

## Behavior

The ingestion service processes one batch per call. This enables the UI to show:

- Progress bar
- Processed / total records
- Created / updated / skipped / failed
- Last processed row
- Resume button behavior

## Upsert Strategy

```text
MCP upsert_vertex
  -> REST fallback
  -> local mock fallback
```

## Validate

```bash
uv run python scripts/validate_ingestion_framework.py
```

## Note

Actual TigerGraph MCP tool names can be adjusted later to match your company's final MCP server contract. The design keeps that integration isolated in `app/ingestion/tigergraph_upsert.py`.
