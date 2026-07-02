# Part 11.10 — Recommendation Engine Package

## Added

- Recommendation models
- Recommendation repository
- Playbook selector
- Compliance validator
- Recommendation generation engine
- Recommendation persistence in SQLite
- TigerGraph recommendation write-back foundation
- Recommendation APIs
- Streamlit Recommendation Engine page foundation
- Explainability evidence and reasoning steps

## API

```text
POST /recommendations/run
POST /recommendations/search
POST /recommendations/status
GET  /recommendations/counts
```

## Validate

```bash
uv run python scripts/validate_recommendation_engine.py
```

## Purpose

This package converts opportunities into explainable, playbook-supported, compliance-aware advisor recommendations. It sets up the foundation for feedback learning in Part 11.11.
