from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
required = [
    "app/api/routers/ui_integrated_expanded.py",
    "app/services/ui_integrated_expanded_service.py",
    "frontend/lib/api/integrated-expanded.ts",
    "frontend/components/advisor360/advisor360-client.tsx",
    "frontend/components/recommendations/opportunities-recommendations-workspace.tsx",
    "frontend/components/graph-explorer/graph-explorer-workspace.tsx",
    "frontend/components/embeddings/embeddings-workspace.tsx",
    "frontend/components/memory-explainability/memory-explainability-workspace.tsx",
    "frontend/components/knowledge/knowledge-workspace.tsx",
    "frontend/components/integrated/common/agent-trace-strip.tsx",
    "frontend/components/integrated/common/status-pill.tsx",
]
missing = [f for f in required if not (ROOT / f).exists()]
report = {
    "status": "passed" if not missing else "failed",
    "missing_files": missing,
    "validated_files": len(required) - len(missing),
    "required_files": len(required),
}
out = ROOT / "docs/part_15_2_validation_report.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
if missing:
    raise SystemExit(1)
