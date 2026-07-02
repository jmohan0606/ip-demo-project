# Known Limitations and External Gates

1. The original uploaded GSQL source files were unavailable during this rebuild. The package establishes a new consolidated Story 1 source of truth from the approved requirements and confirmed logical model.
2. Static review cannot fully reproduce the TigerGraph 4.2.2 compiler or runtime. Live schema creation, query installation and query execution remain mandatory.
3. Mock mode proves loader orchestration and SQLite tracking only; it does not prove RESTPP acceptance by a live graph.
4. No graph reset/delete operation is exposed in the UI. Destructive reset requires a separately approved, authorized procedure.
5. Feature vectors, embeddings, predictions and learning updates are deterministic showcase simulations. Production model training, model registry, drift monitoring and online inference are future work.
6. SQLite is designed for a single local application instance. A production multi-instance deployment would move ingestion operations to a shared durable database and distributed job system.
7. The UI in Story 1 is intentionally limited to graph data management and validation. Persona business pages are Story 2 consumers of this foundation.
8. Live performance and batch-size tuning depend on the target TigerGraph topology, network path and RESTPP limits.
