# Client Demo Handoff Checklist

## Before Demo

```bash
uv sync
cp .env.example .env
uv run python scripts/client_ready_validation.py
```

## Run Backend

```bash
uv run python run_local_api.py
```

## Run UI

```bash
uv run streamlit run app/ui/app_enterprise.py
```

## Pages to Show

1. End-to-End Demo Run
2. Executive Dashboard
3. Agentic AI Console
4. Advisor 360
5. AGP Goals & Coaching
6. Recommendations
7. Feedback Learning
8. AI Assistant Chat
9. Graph Access Status
10. Final Audit & Gap Closure

## Talking Points

- This is now a true agentic architecture.
- Agents use LangGraph/LangChain-ready workflow.
- TigerGraph access is MCP-library first.
- REST is fallback.
- Mock graph is final fallback.
- SQLite and Chroma are preloaded.
- Feedback updates learning signals and context memory.
- Explainability is available through evidence and reasoning steps.
