# Part 15.2 — API-Connected Pages Beyond Dashboard

## Pages connected to backend APIs

- Advisor 360 / Client 360
- Opportunities & Recommendations
- Knowledge Graph Explorer
- Feature Store / Embeddings / Similarity
- Memory Timeline & Explainability
- Knowledge / Chroma Search

## Backend APIs added

```text
POST /ui-integrated/advisor-360
POST /ui-integrated/recommendations/workspace
POST /ui-integrated/graph/explore
POST /ui-integrated/features-embeddings
POST /ui-integrated/memory-explainability
POST /ui-integrated/knowledge/search
```

## Behavior

Every page now follows the pattern:

```text
React page
  → persona/scope/period context
  → FastAPI integrated endpoint
  → backend agent-style service
  → mock/TigerGraph/Chroma/fallback-ready response
  → UI cards, charts, panels and agent trace
```

## Included UX corrections

- Compact page density
- Smaller card sections
- Good/warning/bad color coding
- Agent trace visibility
- Chroma search workflow
- Feature/embedding/similarity workflow
- Graph explorer backend data source
- Memory/evidence/explainability backend source

## Next step

Part 15.3 — Full End-to-End Backend Orchestration:
- Replace mock service internals with real LangGraph orchestration
- Connect TigerGraph MCP-first tools
- Connect Chroma persistent collection
- Connect SQLite feature store
- Persist recommendation feedback and memory updates
