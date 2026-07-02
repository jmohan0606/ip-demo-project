from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
required = [
    "app/recommendations/__init__.py",
    "app/recommendations/models.py",
    "app/recommendations/learning_store.py",
    "app/recommendations/opportunity_engine.py",
    "app/recommendations/recommendation_engine.py",
    "app/recommendations/compliance.py",
    "app/recommendations/learning_engine.py",
    "app/recommendations/recommendation_runtime.py",
    "app/api/routers/recommendation_runtime.py",
    "frontend/lib/api/recommendation-runtime.ts",
    "frontend/components/recommendation-runtime/recommendation-runtime-workspace.tsx",
    "frontend/app/(dashboard)/recommendation-runtime/page.tsx",
]
missing = [f for f in required if not (ROOT / f).exists()]
runtime_text = (ROOT / "app/recommendations/recommendation_runtime.py").read_text(encoding="utf-8")
checks = {
    "opportunity_engine": "OpportunityEngine" in runtime_text,
    "recommendation_engine": "RecommendationEngine" in runtime_text,
    "learning_store": "LearningStore" in runtime_text,
    "graph_persistence": "upsert_vertex" in runtime_text and "persist_recommendation_feedback" in runtime_text,
    "knowledge_evidence": "knowledge.search" in runtime_text,
}
report = {
    "status": "passed" if not missing and all(checks.values()) else "failed",
    "missing_files": missing,
    "validated_files": len(required) - len(missing),
    "required_files": len(required),
    "checks": checks,
}
out = ROOT / "docs/part_15_7_validation_report.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
if report["status"] != "passed":
    raise SystemExit(1)
