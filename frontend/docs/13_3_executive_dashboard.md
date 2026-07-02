# Part 13.3 — Executive Dashboard

## Added

- Executive dashboard React page
- KPI cards for Revenue, AUM, NNM, NCF
- Revenue trend chart
- Product revenue mix chart
- Insights & Coaching expandable cards
- Evidence panel
- Reasoning steps
- Recommended actions
- Top performers table
- Bottom performers table
- AGP status badges
- Dashboard loading skeleton
- API fallback data source

## Dashboard Behavior

The dashboard attempts to call:

```text
POST /ui/executive-dashboard
```

If that endpoint is not available yet, the UI uses local dashboard fallback data so the page remains demoable.

## Validate

```bash
cd frontend
npm run validate:dashboard
```
