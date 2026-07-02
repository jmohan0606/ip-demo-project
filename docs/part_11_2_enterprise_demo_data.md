# Part 11.2 — Enterprise Demo Data Package

## Generated Scale

```json
{
  "firm": 1,
  "divisions": 4,
  "regions": 12,
  "markets": 24,
  "advisors": 168,
  "agp_advisors": 65,
  "households": 2345,
  "accounts": 7053,
  "transactions": 508260,
  "months": 36
}
```

## Included Data Domains

- Firm / Division / Region / Market / Advisor hierarchy
- Persona users
- Households
- Accounts
- Product categories, subcategories, products
- 36 months of time periods
- Transactions with trade date, settlement date, buy/sell flag, quantity, principal amount, revenue, managed revenue, NCF, NNM
- Monthly AUM
- Monthly NCF
- Monthly NNM
- Monthly Product Revenue
- Monthly Eligibility
- CRM activities
- AGP program, goals, KPIs, coaching sessions, manager reviews
- Predictions
- Opportunities
- Recommendations
- Feedback events
- Outcome events
- Learning signals
- Temporal context memories
- Conversation turns
- Reasoning traces
- Documents and chunks
- Playbooks and best practices
- Feature snapshots
- Embeddings
- Similarity matches
- Notifications
- Business glossary

## API

```text
GET /demo-data/manifest
GET /demo-data/files
```

## Validate

```bash
uv run python scripts/validate_demo_data.py
```

## Notes

This package creates CSVs for demo and ingestion. Actual TigerGraph upsert/resumable loading will be implemented in Part 11.3.
