# iPerform Insights & Coaching — Final Consolidated Delivery Package

## Application

**iPerform Insights & Coaching**

A local-machine demo-ready advisor insights and coaching platform for wealth-management use cases.

## Key Capabilities

- Enterprise Streamlit UI with left navigation
- Persona and scope selection
- Advisor 360
- AGP Goals & Coaching
- Data ingestion and resumable sync foundation
- TigerGraph 4.2.2 schema with `phx_dm_` prefix
- Enterprise demo data package
- Chroma-based knowledge/RAG foundation
- Context Graph and Temporal Memory
- SQLite feature store
- Local graph embeddings and similarity
- Local sklearn prediction engine
- Opportunity engine
- Recommendation engine
- Feedback learning loop
- AI Insights & Coaching engine
- AI Assistant Chat as separate page
- End-to-end demo orchestration

## Graph

```text
Graph name: iperform_insights_coaching_demo
Prefix:     phx_dm_
Version:    TigerGraph 4.2.2 compatible / V1-first GSQL
```

## Local Runtime

This package is designed to run locally using:

- Python
- UV package manager
- FastAPI
- Streamlit
- SQLite
- Chroma
- NetworkX
- scikit-learn
- OpenAI adapter with mock fallback
- TigerGraph MCP/REST optional

TigerGraph is not required locally because local mock fallback is supported.
