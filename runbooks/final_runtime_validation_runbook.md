# Final Runtime Validation Runbook

## 1. Install

```bash
uv sync
```

## 2. Run File/Requirement Audit

```bash
uv run python scripts/run_final_audit.py
```

## 3. Run Runtime Validation

```bash
uv run python scripts/run_runtime_validation.py
```

## 4. Run Client Demo Go/No-Go

```bash
uv run python scripts/client_demo_go_no_go.py
```

## 5. Start API

```bash
uv run python run_local_api.py
```

Open:

```text
http://127.0.0.1:8000/docs
```

Call:

```text
GET /runtime-validation/run
```

## 6. Start UI

```bash
uv run streamlit run app/ui/app_enterprise.py
```

Open:

```text
Final Runtime Validation
```

## GO Criteria

- Runtime validation status: passed
- Checks failed: 0
- Final audit status: passed
- Agentic workflow returns answer
- SQLite has recommendations and memory
- Chroma folder/index exists
- Graph access has at least mock fallback
