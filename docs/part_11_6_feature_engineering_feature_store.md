# Part 11.6 — Feature Engineering & Feature Store Package

## Added

- Feature models
- Feature registry
- SQLite feature definition and feature vector tables
- Feature engineering pipelines from demo CSVs
- Advisor growth features
- CRM activity features
- AGP progress features
- Household opportunity features
- Account revenue features
- Feature Store API
- Streamlit Feature Store page foundation

## API

```text
POST /features/materialize
GET  /features/vectors
GET  /features/vector
GET  /features/counts
```

## Validate

```bash
uv run python scripts/validate_feature_store.py
```

## Purpose

This package creates the local machine feature store used by predictions, recommendations, similarity, opportunities, explainability, and scenario simulation.
