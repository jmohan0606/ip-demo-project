from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
required = [
    "app/api/routers/ui_integrated.py",
    "app/services/ui_integrated_service.py",
    "frontend/lib/api/integrated-ui.ts",
    "frontend/components/integrated-dashboard/integrated-dashboard-client.tsx",
    "frontend/components/integrated-dashboard/compact-kpi-card.tsx",
    "frontend/components/integrated-dashboard/action-button.tsx",
    "frontend/components/documents/document-ingestion-workspace.tsx",
    "frontend/app/(dashboard)/dashboard/page.tsx",
    "frontend/app/(dashboard)/what-if/page.tsx",
    "frontend/app/(dashboard)/document-ingestion/page.tsx",
]
missing = [f for f in required if not (ROOT / f).exists()]
report = {"status": "passed" if not missing else "failed", "missing_files": missing, "validated_files": len(required)-len(missing), "required_files": len(required)}
out = ROOT / "docs/part_15_1_validation_report.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
if missing: raise SystemExit(1)
