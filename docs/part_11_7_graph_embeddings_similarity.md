# Part 11.7 — Graph Embeddings & Similarity Package

## Added

- NetworkX demo graph builder
- Local graph-signature embedding engine
- Cosine similarity engine
- Advisor peer similarity
- Household similarity
- SQLite embedding and similarity persistence
- TigerGraph embedding/similarity linker
- Embedding and similarity APIs
- Streamlit Embeddings & Similarity page foundation

## API

```text
POST /embeddings/build
GET  /embeddings/list
POST /embeddings/similarity/search
GET  /embeddings/similarity/list
GET  /embeddings/counts
```

## Validate

```bash
uv run python scripts/validate_embeddings_similarity.py
```

## Note

This package intentionally uses local, lightweight graph algorithms rather than heavy ML frameworks. It is demo-realistic and can later be replaced with GraphSAGE, node2vec, or a GNN pipeline.
