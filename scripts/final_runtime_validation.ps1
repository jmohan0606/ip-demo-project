$ErrorActionPreference = "Stop"

Write-Host "Running final static validations..."
uv run python scripts/validate_part_16_3.py
uv run python scripts/validate_part_16_2.py
uv run python scripts/validate_part_16_1.py
uv run python scripts/validate_part_15_8.py
uv run python scripts/validate_part_15_7.py
uv run python scripts/validate_part_15_6.py
uv run python scripts/validate_part_15_5.py
uv run python scripts/validate_part_15_4.py
uv run python scripts/validate_part_15_3.py
uv run python scripts/runtime_preflight.py

Write-Host "Static validation complete."
Write-Host "For API health checks, start API first: uv run python run_local_api.py"
Write-Host "Then run: uv run python scripts/final_api_health_check.py"
Write-Host "For browser screenshots, start frontend first: cd frontend; npm run dev"
Write-Host "Then run: uv run python scripts/capture_browser_screenshots.py"
