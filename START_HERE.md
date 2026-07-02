# START HERE — iPerform Insights & Coaching

## Quickest local run

```bash
uv sync
uv run python scripts/final_release_check.py
uv run python run_local_api.py
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:3000/dashboard
```

## Most important docs

1. `docs/FINAL_RELEASE_README.md`
2. `docs/final_requirements_coverage_matrix.md`
3. `docs/part_16_4_final_runtime_build_screenshot_validation.md`
4. `docs/part_16_2_production_data_load_schema_gsql.md`
5. `docs/part_16_3_real_azure_openai_llm_agent_activation.md`
