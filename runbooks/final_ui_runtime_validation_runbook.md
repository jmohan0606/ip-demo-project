# Final UI Runtime Validation Runbook

## 1. Start backend

```bash
uv run python run_local_api.py
```

## 2. Install and validate frontend

```bash
cd frontend
npm install
npm run validate:final-ui
npm run validate:runtime
npm run build
```

## 3. Start frontend

```bash
npm run dev
```

Open:

```text
http://localhost:3000
```

## 4. Optional screenshot capture

```bash
npx playwright install chromium
npm run screenshots
```

## 5. Review screenshots

Check each page against approved mockup style:

- Executive Dashboard
- Revenue Analytics
- Advisor 360
- AGP
- What-If
- Predictions
- Recommendations
- ROI
- AI Assistant
- Knowledge
- Graph Explorer
- Feature Store / Embeddings
- Memory / Explainability
- Observability
- Data Ingestion
- Admin Health

## Next step

Client-ready visual review and targeted UI fixes if screenshots show mismatch.
