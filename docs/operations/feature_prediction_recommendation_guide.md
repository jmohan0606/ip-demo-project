# Feature, Prediction, Opportunity, and Recommendation Guide

## Feature Store

Run:

```bash
uv run python scripts/materialize_features.py
```

UI:

```text
Feature Store -> Materialize Features
```

## Embeddings & Similarity

Run:

```bash
uv run python scripts/build_embeddings_similarity.py
```

UI:

```text
Graph Embeddings & Similarity -> Build
```

## Predictions

Run:

```bash
uv run python scripts/run_predictions.py
```

Prediction types:

- Revenue Growth
- NNM Growth
- AUM Growth
- AGP Goal Risk
- Advisor Success Score
- Opportunity Propensity

## Opportunities

Run:

```bash
uv run python scripts/run_opportunities.py
```

Opportunity types:

- Managed Account Expansion
- NNM Growth
- AUM Retention
- AGP Goal Recovery
- CRM Engagement Gap
- Peer Benchmark Gap

## Recommendations

Run:

```bash
uv run python scripts/run_recommendations.py
```

Recommendations are:

- Playbook-supported
- Compliance checked
- Evidence-backed
- Explainable
- Feedback-enabled
