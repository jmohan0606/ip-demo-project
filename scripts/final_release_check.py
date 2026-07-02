from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "README.md",
    "docs/FINAL_RELEASE_README.md",
    "docs/final_requirements_coverage_matrix.md",
    "docs/final_release_status.json",
    "run_local_api.py",
    "app/api/main.py",
    "app/orchestration/engine.py",
    "app/graph/graph_runtime.py",
    "app/knowledge/knowledge_runtime.py",
    "app/features/feature_runtime.py",
    "app/recommendations/recommendation_runtime.py",
    "app/memory/memory_runtime.py",
    "app/llm/llm_runtime.py",
    "frontend/app/(dashboard)/dashboard/page.tsx",
    "scripts/final_runtime_validation.sh",
    "scripts/final_api_health_check.py",
    "scripts/capture_browser_screenshots.py",
]

missing = [item for item in REQUIRED if not (ROOT / item).exists()]
report = {
    "status": "passed" if not missing else "failed",
    "required_files": len(REQUIRED),
    "validated_files": len(REQUIRED) - len(missing),
    "missing_files": missing,
}
out = ROOT / "docs/final_release_check_report.json"
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
if missing:
    raise SystemExit(1)
