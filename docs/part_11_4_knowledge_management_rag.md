# Part 11.4 — Knowledge Management & RAG Package

## Added

- Sample knowledge documents
- Document parser
- Text chunker
- Embedding service using model adapter
- Chroma vector store integration
- Knowledge document catalog in SQLite
- TigerGraph document/chunk linker using MCP/REST/local fallback
- Knowledge ingestion service
- Knowledge search service
- Knowledge Management API
- Streamlit Knowledge Management page foundation

## API

```text
POST /knowledge/ingest
POST /knowledge/ingest-samples
POST /knowledge/search
GET  /knowledge/documents
```

## Validate

```bash
uv run python scripts/validate_knowledge_management.py
```
