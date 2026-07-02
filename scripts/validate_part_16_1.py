from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
required = [
    "app/graph/tigergraph_mcp_contracts.py",
    "app/graph/tigergraph_production_runtime.py",
    "app/api/routers/tigergraph_activation.py",
    "frontend/lib/api/tigergraph-activation.ts",
    "frontend/components/tigergraph-activation/tigergraph-activation-workspace.tsx",
    "frontend/app/(dashboard)/tigergraph-activation/page.tsx",
    "gsql/production_query_contracts/README.md",
    "scripts/tigergraph_activation_smoke_test.py",
]
missing = [f for f in required if not (ROOT / f).exists()]
runtime_text = (ROOT / "app/graph/tigergraph_production_runtime.py").read_text(encoding="utf-8")
checks = {
    "logical_contracts": "QUERY_CONTRACTS" in runtime_text,
    "smoke_test": "activate_smoke_test" in runtime_text,
    "production_data_activation": "production_data_activation" in runtime_text,
    "mcp_first_graph_runtime": "get_graph_runtime" in runtime_text,
}
report = {
    "status": "passed" if not missing and all(checks.values()) else "failed",
    "missing_files": missing,
    "validated_files": len(required) - len(missing),
    "required_files": len(required),
    "checks": checks,
}
out = ROOT / "docs/part_16_1_validation_report.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
if report["status"] != "passed":
    raise SystemExit(1)
