from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

required = [
    "app/graph/tigergraph_schema_contracts.py",
    "gsql/schema/iperform_enterprise_schema.gsql",
    "gsql/loading/production_loading_job.gsql",
    "gsql/queries/get_advisor_context.gsql",
    "gsql/queries/get_revenue_summary.gsql",
    "gsql/queries/get_advisor_360.gsql",
    "gsql/queries/get_recommendation_context.gsql",
    "gsql/queries/get_memory_timeline.gsql",
    "gsql/queries/get_graph_explorer.gsql",
    "scripts/verify_tigergraph_schema_contracts.py",
    "scripts/install_tigergraph_gsql_queries.sh",
    "scripts/install_tigergraph_gsql_queries.ps1",
]
missing = [f for f in required if not (ROOT / f).exists()]
schema_text = (ROOT / "gsql/schema/iperform_enterprise_schema.gsql").read_text(encoding="utf-8")
checks = {
    "schema_has_graph": "CREATE GRAPH iPerformInsights" in schema_text,
    "loading_job_exists": (ROOT / "gsql/loading/production_loading_job.gsql").exists(),
    "queries_count": len(list((ROOT / "gsql/queries").glob("*.gsql"))) >= 6,
}
report = {
    "status": "passed" if not missing and all(checks.values()) else "failed",
    "missing_files": missing,
    "validated_files": len(required) - len(missing),
    "required_files": len(required),
    "checks": checks,
}
out = ROOT / "docs/part_16_2_validation_report.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
if report["status"] != "passed":
    raise SystemExit(1)
