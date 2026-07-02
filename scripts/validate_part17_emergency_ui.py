from pathlib import Path
import json
ROOT = Path(__file__).resolve().parents[1]
required = [
 "app/api/routers/ui_remediation.py",
 "frontend/lib/api/ui-remediation.ts",
 "frontend/components/remediation/dense-ui.tsx",
 "frontend/app/(dashboard)/dashboard/page.tsx",
 "frontend/app/(dashboard)/revenue-analytics/page.tsx",
 "frontend/app/(dashboard)/advisor-360/page.tsx",
 "frontend/app/(dashboard)/recommendations/page.tsx",
 "frontend/app/(dashboard)/graph-explorer/page.tsx",
 "frontend/app/(dashboard)/features-embeddings/page.tsx",
 "frontend/app/(dashboard)/memory-explainability/page.tsx",
 "frontend/app/(dashboard)/data-ingestion/page.tsx",
]
missing=[f for f in required if not (ROOT/f).exists()]
report={"status":"passed" if not missing else "failed","missing_files":missing,"validated_files":len(required)-len(missing),"required_files":len(required)}
(ROOT/"docs/part17_emergency_ui_validation.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(report,indent=2))
if missing: raise SystemExit(1)
