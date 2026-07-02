# Part 15.5 — Chroma & Knowledge Services

## Added

- Knowledge runtime service
- Document chunker
- Deterministic local embedding fallback
- Optional persistent Chroma adapter
- JSON-backed persistent vector store fallback
- Document ingestion API
- Upload API
- Knowledge search API
- Knowledge runtime status API
- Graph lineage for documents and chunks through GraphRuntime
- UI page for Chroma runtime

## Runtime order

```text
KnowledgeRuntime
  1. Chroma PersistentClient, if chromadb is installed
  2. MockPersistentVectorStore JSON fallback
  3. GraphRuntime writes document/chunk lineage through MCP -> REST -> mock
```

## APIs

```text
GET  /knowledge-runtime/status
POST /knowledge-runtime/search
POST /knowledge-runtime/ingest
POST /knowledge-runtime/upload
```

## Environment

```text
CHROMA_PERSIST_DIR=data/chroma
CHROMA_COLLECTION_NAME=iperform_knowledge_base
DOCUMENTS_DIR=data/documents
EMBEDDING_BACKEND=chroma
```

## Next step

Part 15.6 — Feature Store & Prediction Platform.
