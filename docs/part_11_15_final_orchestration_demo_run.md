# Part 11.15 — Final Orchestration & End-to-End Demo Run Package

## Added

- End-to-end demo orchestrator
- Full local demo pipeline
- Demo run API
- Streamlit End-to-End Demo Run page
- Run scripts
- Final validation script
- Local demo runbook

## API

```text
POST /demo-run/full?advisor_id=ADV0001
```

## Run

```bash
uv run python scripts/validate_final_demo.py
uv run python run_local_api.py
uv run streamlit run app/ui/app_enterprise.py
```

## Pipeline

```text
Knowledge Ingestion
  -> Feature Materialization
  -> Graph Embeddings & Similarity
  -> Predictions
  -> Opportunities & Recommendations
  -> Feedback Learning
  -> AI Insights & Coaching
```
