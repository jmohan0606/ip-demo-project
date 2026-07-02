# Part 11.5 — Context Graph & Temporal Memory Package

## Added

- Context memory models
- Memory repository using SQLite
- TigerGraph memory linker using MCP/REST/local fallback
- Memory service
- Context package service
- Conversation turn persistence
- Reasoning trace persistence
- Memory API endpoints
- Memory Timeline Streamlit page foundation
- V1 GSQL memory queries

## API

```text
POST /memory/create
POST /memory/retrieve
POST /memory/context-package
POST /memory/conversation-turn
POST /memory/reasoning-trace
GET  /memory/counts
```

## Validate

```bash
uv run python scripts/validate_memory_context.py
```
