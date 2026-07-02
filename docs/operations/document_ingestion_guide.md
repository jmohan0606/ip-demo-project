# Document Ingestion Guide

## Sample Documents

Bundled documents are stored in:

```text
data/documents/sample_knowledge/
```

Examples:

- Managed account growth playbook
- AGP coaching guide
- Compliance recommendation policy
- NNM/AUM/NCF glossary

## UI Ingestion

1. Open Streamlit
2. Go to **Knowledge Management**
3. Click **Ingest Sample Knowledge**
4. Search documents in the **Search** tab

## Script Ingestion

```bash
uv run python scripts/ingest_sample_knowledge.py
```

## API Ingestion

```text
POST /knowledge/ingest-samples
POST /knowledge/ingest
POST /knowledge/search
GET  /knowledge/documents
```

## How It Works

```text
Document
  -> Parse
  -> Chunk
  -> Embed
  -> Store in Chroma
  -> Catalog in SQLite
  -> Link document/chunks to TigerGraph through MCP/REST/Mock
```
