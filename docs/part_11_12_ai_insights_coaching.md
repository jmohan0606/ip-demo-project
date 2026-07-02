# Part 11.12 — AI Insights & Coaching Engine Package

## Added

- Insight and coaching models
- AI prompt foundation
- Insight data collector
- Insight generation engine
- Insight repository
- TigerGraph reasoning trace write-back
- Memory update integration
- AI Insights & Coaching API
- Streamlit AI Insights & Coaching page
- V1 GSQL evidence query

## API

```text
POST /insights-coaching/generate
GET  /insights-coaching/cards
GET  /insights-coaching/counts
```

## Validate

```bash
uv run python scripts/validate_insights_coaching.py
```

## Purpose

This package unifies feature store, predictions, opportunities, recommendations, feedback memory, context graph, and AI generation into advisor-ready insight cards and coaching plans.
