# Loading / Upsert Strategy

This rebuild does not depend on TigerGraph Studio manual mapping as the primary ingestion path.

Preferred flow:

```text
CSV / CRM / Documents
  -> Python validation
  -> Delta detection
  -> Checkpoint tracking in SQLite
  -> TigerGraph MCP upsert
  -> TigerGraph REST fallback
```

Studio loading jobs can still be used for initial bulk upload if needed, but the application will include a resumable ingestion service in Part 11.3.
