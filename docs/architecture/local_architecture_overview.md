# Local Architecture Overview

```text
Streamlit UI
    |
FastAPI APIs
    |
Application Services
    |
+----------------------+-----------------------+
| Intelligence Engines | Graph Access Layer    |
+----------------------+-----------------------+
| Feature Store        | MCP first             |
| Embeddings           | REST fallback         |
| Predictions          | Mock fallback         |
| Opportunities        |                       |
| Recommendations      |                       |
| Feedback Learning    |                       |
| Insights & Coaching  |                       |
| AI Chat              |                       |
+----------------------+-----------------------+
    |
SQLite + Chroma + Demo CSVs
    |
Optional TigerGraph AWS
```

## Graph Access

```text
GraphAccessClient
  -> TigerGraph MCP Client
  -> TigerGraph REST Client
  -> Mock Graph Data Service
```

## Persistence

Local:

- SQLite for feature vectors, predictions, recommendations, feedback, memory, chat
- Chroma for document chunks and embeddings
- CSVs for enterprise demo seed data

External optional:

- TigerGraph in AWS
- Existing TigerGraph MCP server
