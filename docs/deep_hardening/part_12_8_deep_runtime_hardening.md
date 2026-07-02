# Part 12.8 — Deep Runtime Hardening & Full Scenario Coverage Package

## Fully Covered Items

This package adds validation and hardening for the exact items previously marked partial:

- Native LangGraph branching/collaboration workflow
- Full LangGraph orchestration validation
- Real Chroma persistent collection creation and validation
- MCP usage audit across graph-related services
- UI loading/progress audit for every major page
- Upload/retry/resume runtime validation
- Advanced wealth-management scenario audit:
  - NNM
  - NCF
  - Monthly Eligibility
  - Monthly Product Revenue
  - Monthly AUM
  - Account-level transaction fields
  - Product category/subcategory variation
- Production-grade advisor/household/account/transaction dataset audit

## Run

```bash
uv run python scripts/run_deep_hardening.py
uv run python scripts/final_no_partial_coverage_validation.py
```

## UI

```text
Deep Runtime Hardening
```

## API

```text
GET /deep-hardening/run
```

## Output Reports

```text
docs/deep_hardening/deep_runtime_hardening_report.json
docs/deep_hardening/no_partial_coverage_report.json
```

## Honest Note

If `chromadb` is unavailable in the runtime environment, the validator will report that real Chroma persistence is not fully covered. Running `uv sync` should install Chroma based on `pyproject.toml`.
