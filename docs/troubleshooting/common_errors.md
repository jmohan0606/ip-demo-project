# Troubleshooting Guide

## `uv` not found

Install UV and restart terminal.

## Import error

Run:

```bash
uv sync
```

Then:

```bash
uv run python scripts/final_smoke_test.py
```

## Streamlit page does not load

Run:

```bash
uv run streamlit run app/ui/app_enterprise.py
```

Check Python version is 3.11+.

## API does not start

Run:

```bash
uv run python run_local_api.py
```

Check port 8000 is free.

## MCP unavailable

Run:

```bash
uv run python scripts/validate_graph_access.py
```

If MCP fails, confirm:

- `TIGERGRAPH_MCP_URL`
- API key/header
- MCP server is running
- Tool names match `.env`

## TigerGraph REST unavailable

Confirm:

- `TIGERGRAPH_HOST`
- Graph name
- Credentials
- Network/VPN access

## Demo still works but shows mock mode

This is expected if MCP and REST are unavailable. The final fallback is local mock graph service.

## Chroma errors

Delete local Chroma directory if corrupted, then re-ingest documents.

## No recommendations

Run:

```bash
uv run python scripts/run_predictions.py
uv run python scripts/run_opportunities.py
uv run python scripts/run_recommendations.py
```

Or use **End-to-End Demo Run** in the UI.
