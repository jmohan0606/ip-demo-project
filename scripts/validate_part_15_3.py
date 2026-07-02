from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
required = [
    "app/orchestration/__init__.py",
    "app/orchestration/state.py",
    "app/orchestration/tools.py",
    "app/orchestration/agents.py",
    "app/orchestration/engine.py",
    "app/api/routers/orchestration.py",
    "frontend/lib/api/orchestration.ts",
    "frontend/components/orchestration/orchestration-workspace.tsx",
    "frontend/app/(dashboard)/orchestration/page.tsx",
]
missing = [f for f in required if not (ROOT / f).exists()]
report = {"status": "passed" if not missing else "failed", "missing_files": missing, "validated_files": len(required)-len(missing), "required_files": len(required)}
out = ROOT / "docs/part_15_3_validation_report.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
if missing: raise SystemExit(1)
