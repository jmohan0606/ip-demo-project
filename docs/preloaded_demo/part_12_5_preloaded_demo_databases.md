# Part 12.5 — Preloaded Demo Databases Package

## Added

Physical preloaded demo databases:

```text
data/sqlite/iperform.db
data/chroma/
data/preloaded/preloaded_demo_database_manifest.json
```

## Preloaded SQLite Content

- Feature definitions
- Feature vectors
- Graph embeddings
- Similarity matches
- Predictions
- Opportunities
- Recommendations
- Feedback events
- Outcome events
- Learning signals
- Context memories
- Conversation history
- Reasoning traces
- Knowledge document catalog
- Insight cards
- Coaching plans

## Preloaded Chroma Content

The package includes:

```text
data/chroma/preloaded_chroma_manifest.json
data/chroma/preloaded_knowledge_index.json
```

If Chroma is available during build/runtime, a persistent Chroma collection is also created in the same folder.

## Validate

```bash
uv run python scripts/validate_preloaded_demo_databases.py
```

## Why This Matters

The Streamlit UI can now show meaningful demo content immediately, without needing to first run every generation pipeline.
