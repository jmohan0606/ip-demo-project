# Deep Hardening Runbook

## Step 1

```bash
uv sync
```

## Step 2

```bash
uv run python scripts/run_runtime_validation.py
```

## Step 3

```bash
uv run python scripts/run_deep_hardening.py
```

## Step 4

```bash
uv run python scripts/final_no_partial_coverage_validation.py
```

## Step 5

Open UI:

```bash
uv run streamlit run app/ui/app_enterprise.py
```

Go to:

```text
Deep Runtime Hardening
```

## Pass Criteria

- Runtime validation passed
- Deep hardening passed
- Real Chroma persistent collection ready
- MCP usage audit passed
- UI progress audit passed
- Upload resume validation passed
- Wealth scenario audit passed
- Dataset expansion audit passed
