# Part 11.11 — Feedback Learning Package

## Added

- Feedback event models
- Outcome event models
- Learning signal models
- Feedback repository
- Reward scoring engine
- Learning signal generator
- TigerGraph feedback/outcome/learning write-back foundation
- Recommendation status update integration
- Context memory update integration
- Feedback Learning API
- Streamlit Feedback Learning page foundation
- V1 GSQL feedback query

## API

```text
POST /feedback-learning/submit
POST /feedback-learning/search
GET  /feedback-learning/learning-signals
GET  /feedback-learning/counts
```

## Validate

```bash
uv run python scripts/validate_feedback_learning.py
```

## End-to-End Flow

```text
Recommendation
  -> Feedback Event
  -> Outcome Event
  -> Learning Signal
  -> Recommendation Status Update
  -> Context Memory Update
  -> TigerGraph Write-back
```
