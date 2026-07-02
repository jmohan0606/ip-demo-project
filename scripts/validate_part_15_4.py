from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
required = [
    "app/graph/__init__.py",
    "app/graph/models.py",
    "app/graph/tigergraph_mcp_adapter.py",
    "app/graph/tigergraph_rest_adapter.py",
    "app/graph/mock_graph_store.py",
    "app/graph/graph_runtime.py",
    "app/api/routers/graph_runtime.py",
    "app/orchestration/tools.py",
    "frontend/lib/api/graph-runtime.ts",
    "frontend/components/graph-runtime/graph-runtime-workspace.tsx",
    "frontend/app/(dashboard)/graph-runtime/page.tsx",
]
missing = [f for f in required if not (ROOT / f).exists()]
text_checks = {
    "mcp_first": "TigerGraphMcpAdapter" in (ROOT / "app/graph/graph_runtime.py").read_text(encoding="utf-8"),
    "rest_fallback": "TigerGraphRestAdapter" in (ROOT / "app/graph/graph_runtime.py").read_text(encoding="utf-8"),
    "mock_fallback": "MockGraphStore" in (ROOT / "app/graph/graph_runtime.py").read_text(encoding="utf-8"),
    "tool_runtime_uses_graph": "get_graph_runtime" in (ROOT / "app/orchestration/tools.py").read_text(encoding="utf-8"),
}
report = {
    "status": "passed" if not missing and all(text_checks.values()) else "failed",
    "missing_files": missing,
    "validated_files": len(required) - len(missing),
    "required_files": len(required),
    "text_checks": text_checks,
}
out = ROOT / "docs/part_15_4_validation_report.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
if report["status"] != "passed":
    raise SystemExit(1)
