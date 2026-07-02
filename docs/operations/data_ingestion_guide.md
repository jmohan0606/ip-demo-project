# Data Ingestion & Synchronization Guide

## UI Upload Flow

1. Open **Data Ingestion & Sync**
2. Select entity
3. Choose dry run or actual upload
4. Click **Run Next Batch**
5. Watch progress bar and status
6. Resume failed/incomplete uploads if needed

## Upload Path

```text
UI
  -> Ingestion Service
  -> Validation
  -> Delta Detection
  -> SQLite Checkpoint
  -> GraphAccessClient
  -> MCP
  -> REST
  -> Mock
```

## Supported Entities

- Advisor
- Household
- Account
- Transaction
- CRM Activity
- AGP Goal
- KPI
- Prediction
- Opportunity
- Recommendation
- Feedback
- Memory
- Document
- Feature Snapshot
- Embedding

## API

```text
GET  /ingestion/entities
GET  /ingestion/batches
POST /ingestion/run
```

## Resume Behavior

The ingestion service stores:

- batch_id
- entity_name
- file_name
- processed rows
- failed row
- created/updated/skipped counts
- progress percent

If upload fails, rerun with `resume=true`.
