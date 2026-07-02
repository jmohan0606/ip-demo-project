# Part 13.1 — UI Architecture & Design System

This starts the React/Next.js enterprise UI rebuild and replaces the Streamlit UI direction.

## Included

- Next.js + TypeScript + Tailwind setup
- ShadCN-style component foundation
- Enterprise app shell
- Left navigation
- Top header
- Persona/scope/time-period selector
- Runtime mode pill
- Global loading overlay
- KPI card component
- Executive dashboard shell
- Placeholder pages for every approved menu
- FastAPI client layer
- UI architecture validation script

## Menus Locked

- Executive Dashboard
- Revenue Analytics
- Advisor 360 / Client 360
- AGP Goals & Coaching
- What-If Simulator
- Opportunities & Recommendations
- Recommendation Impact / ROI
- AI Assistant
- Knowledge / Playbooks / Compliance
- Knowledge Graph Explorer
- Feature Store / Embeddings / Similarity
- Memory Timeline & Explainability
- Agent Orchestration & Observability
- Data Ingestion & Sync
- Admin / Data Quality / Runtime Health

## Run

```bash
cd frontend
npm install
npm run validate:ui
npm run dev
```

Backend expected at:

```text
http://127.0.0.1:8000
```
