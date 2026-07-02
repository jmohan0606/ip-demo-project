# End-to-End Demo Operations Guide

## Recommended Demo Flow

1. Start Streamlit
2. Open **End-to-End Demo Run**
3. Click **Run Full Demo Pipeline**
4. Open **Executive Dashboard**
5. Click **Generate Dashboard Insights**
6. Review **Insights & Coaching Cards**
7. Open **Advisor 360**
8. Open **Recommendations**
9. Accept or reject a recommendation in **Feedback Learning**
10. Open **AI Assistant Chat**
11. Ask:
   - Why is my revenue low?
   - What should I do next?
   - What evidence supports this recommendation?
   - What changed after feedback?

## Backend Pipeline

```text
Knowledge Ingestion
  -> Feature Materialization
  -> Graph Embeddings & Similarity
  -> Prediction Engine
  -> Opportunity Engine
  -> Recommendation Engine
  -> Feedback Learning
  -> Context Memory
  -> Insights & Coaching
  -> AI Assistant Chat
```

## API Demo

Start API:

```bash
uv run python run_local_api.py
```

Open:

```text
http://127.0.0.1:8000/docs
```

Run:

```text
POST /demo-run/full?advisor_id=ADV0001
```
