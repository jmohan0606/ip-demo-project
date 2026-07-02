# Part 11.9 — Opportunity Engine Package

## Added

- Opportunity models
- Opportunity scoring engine
- Managed account expansion opportunities
- NNM growth opportunities
- AUM retention opportunities
- AGP goal recovery opportunities
- CRM engagement gap opportunities
- Opportunity persistence in SQLite
- TigerGraph opportunity write-back foundation
- Opportunity APIs
- Streamlit Opportunity Engine page foundation

## API

```text
POST /opportunities/run
POST /opportunities/search
GET  /opportunities/counts
```

## Validate

```bash
uv run python scripts/validate_opportunity_engine.py
```

## Purpose

This package turns predictions/features into ranked, explainable advisor opportunities that will feed the Recommendation Engine in Part 11.10.
