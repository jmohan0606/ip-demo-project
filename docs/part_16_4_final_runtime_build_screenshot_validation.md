# Part 16.4 — Final Runtime Build Fixes + Real Browser Screenshot Validation

## Added

- Runtime preflight script
- Final API health check script
- Browser screenshot capture script
- Linux/macOS final validation runner
- Windows final validation runner
- Real screenshot output folder: `docs/real_browser_screenshots`
- Final runtime troubleshooting guidance

## Important note

The package includes the screenshot automation needed for real browser screenshots.

In this sandbox, I cannot reliably install and run the full Node/Next dependency tree for real browser screenshots. The real screenshots must be captured from the running application on your machine using:

```bash
uv run python run_local_api.py
cd frontend
npm install
npm run dev
uv run python scripts/capture_browser_screenshots.py
```

## Validation commands

Static validation:

```bash
bash scripts/final_runtime_validation.sh
```

API health check:

```bash
uv run python run_local_api.py
uv run python scripts/final_api_health_check.py
```

Browser screenshots:

```bash
cd frontend
npm run dev
cd ..
uv run python scripts/capture_browser_screenshots.py
```

## What the screenshot script captures

- Dashboard
- Advisor 360
- What-If
- Recommendation Runtime
- Feature Runtime
- Memory Runtime
- Knowledge Runtime
- Graph Runtime
- TigerGraph Activation
- LLM Activation
- Orchestration

## Next step

Part 16.5 — Final Consolidated Working Package.
