from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
required = [
    "app/features/__init__.py",
    "app/features/models.py",
    "app/features/sqlite_feature_store.py",
    "app/features/feature_engineering.py",
    "app/features/similarity.py",
    "app/features/prediction_runtime.py",
    "app/features/feature_runtime.py",
    "app/api/routers/feature_runtime.py",
    "frontend/lib/api/feature-runtime.ts",
    "frontend/components/feature-runtime/feature-runtime-workspace.tsx",
    "frontend/app/(dashboard)/feature-runtime/page.tsx",
]
missing = [f for f in required if not (ROOT / f).exists()]
runtime_text = (ROOT / "app/features/feature_runtime.py").read_text(encoding="utf-8")
checks = {
    "sqlite_feature_store": "SQLiteFeatureStore" in runtime_text,
    "prediction_runtime": "PredictionRuntime" in runtime_text,
    "similarity_service": "SimilarityService" in runtime_text,
    "graph_persistence": "upsert_vertex" in runtime_text,
}
report = {
    "status": "passed" if not missing and all(checks.values()) else "failed",
    "missing_files": missing,
    "validated_files": len(required) - len(missing),
    "required_files": len(required),
    "checks": checks,
}
out = ROOT / "docs/part_15_6_validation_report.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
if report["status"] != "passed":
    raise SystemExit(1)
