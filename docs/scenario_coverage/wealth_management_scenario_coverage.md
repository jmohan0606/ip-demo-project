# Wealth Management Scenario Coverage

## Covered Data Scenarios

- Advisor hierarchy
- Households
- Accounts
- Transactions
- Trade date
- Settlement date
- Buy/Sell flag
- Quantity
- Principal amount
- Revenue amount
- Net New Money
- Net Cash Flow
- Product category
- Product subcategory
- Monthly AUM
- Monthly Eligibility
- Monthly Product Revenue
- CRM activities
- AGP goals
- AGP KPIs
- Opportunities
- Recommendations
- Feedback
- Learning signals
- Context memory

## Validation

Run:

```bash
uv run python scripts/run_deep_hardening.py
```

The wealth scenario auditor checks that required files exist, have rows, include key transaction columns, and contain enough variation for demo use cases.
