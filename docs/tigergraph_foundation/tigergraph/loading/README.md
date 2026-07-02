# Loading Jobs

The application loader uses TigerGraph RESTPP upsert endpoints because it needs per-batch progress, resumability, row errors, and SQLite checkpoints. This folder contains conventional loading-job guidance for teams that later choose server-side TigerGraph loading jobs.

Use `data/manifest.json` as the authoritative file-to-target mapping. Generate enterprise loading jobs only after confirming the target TigerGraph deployment's file-source and security configuration.
