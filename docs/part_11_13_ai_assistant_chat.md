# Part 11.13 — AI Assistant Chat Package

## Added

- AI chat request/response models
- Chat context assembler
- Chat engine
- Chat repository
- AI Assistant Chat service
- Conversation memory persistence
- Chat API
- Streamlit chat page
- V1 GSQL conversation memory query

## API

```text
POST /ai-chat/ask
GET  /ai-chat/history
```

## Validate

```bash
uv run python scripts/validate_ai_chat.py
```

## Context Sources

The AI Assistant can use:

- Context memory
- Knowledge/RAG
- Insights
- Predictions
- Opportunities
- Recommendations

## Purpose

This package provides the separate AI Assistant chat page requested by the user, while preserving the production architecture of context retrieval, grounding, answer generation, conversation persistence, and future memory use.
