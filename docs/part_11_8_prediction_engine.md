# Part 11.8 — Prediction Engine Package

## Added

- Prediction models and schemas
- Feature matrix builder from SQLite feature store
- sklearn local prediction engine
- Revenue growth prediction
- NNM growth prediction
- AUM growth prediction
- AGP goal risk prediction
- Advisor success score
- Opportunity propensity score
- Prediction repository
- Model metadata tracking
- TigerGraph prediction write-back foundation
- Prediction APIs
- Streamlit Prediction Engine page foundation

## API

```text
POST /predictions/run
POST /predictions/search
GET  /predictions/counts
GET  /predictions/models
```

## Validate

```bash
uv run python scripts/validate_prediction_engine.py
```

## Note

The implementation uses sklearn with synthetic labels generated from demo feature signals. It is suitable for a local production-feel demo and can later be replaced with trained enterprise models.
