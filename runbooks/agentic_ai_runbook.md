# Agentic AI Runbook

## Validate

```bash
uv run python scripts/validate_agentic_architecture.py
```

## API

```text
GET  /agentic-ai/agents
POST /agentic-ai/run
```

## UI

```text
Agentic AI Console
```

## SMARTSDK Replacement Path

Replace `app/agents/tools/service_tools.py` methods with SMARTSDK tool calls while keeping the agent state, registry, route, and response contracts.
