from __future__ import annotations
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
required = [
"frontend/components/remediation/dense-ui.tsx","frontend/lib/api/ui-remediation.ts",
"frontend/app/(dashboard)/dashboard/page.tsx","frontend/app/(dashboard)/revenue-analytics/page.tsx",
"frontend/app/(dashboard)/advisor-360/page.tsx","frontend/app/(dashboard)/recommendations/page.tsx",
"frontend/app/(dashboard)/graph-explorer/page.tsx","frontend/app/(dashboard)/features-embeddings/page.tsx",
"frontend/app/(dashboard)/memory-explainability/page.tsx","frontend/app/(dashboard)/data-ingestion/page.tsx",
"app/api/routers/ui_remediation.py","tigergraph/schema/phx_dm_iperform_enterprise_schema.gsql",
"tigergraph/queries_v1/phx_dm_get_advisor_context.gsql","tigergraph/queries_v1/phx_dm_get_revenue_summary.gsql",
"scripts/load_tigergraph_sample_data_restpp.py","scripts/install_tigergraph_source_of_truth.sh",
"app/graph/tigergraph_mcp_query_contracts.py","app/graph/tigergraph_rest_adapter.py",".env.example"]
missing=[f for f in required if not (ROOT/f).exists()]
schema=(ROOT/"tigergraph/schema/phx_dm_iperform_enterprise_schema.gsql").read_text(encoding="utf-8")
contracts=(ROOT/"app/graph/tigergraph_mcp_query_contracts.py").read_text(encoding="utf-8")
env=(ROOT/".env.example").read_text(encoding="utf-8")
checks={"ui_remediation_present":(ROOT/"frontend/components/remediation/dense-ui.tsx").exists(),
"tg_source_truth_present":"CREATE VERTEX phx_dm_advisor" in schema,
"graph_name_correct":"iperform_insights_coaching_demo" in schema and "TG_GRAPHNAME=iperform_insights_coaching_demo" in env,
"query_contracts_prefixed":"phx_dm_get_advisor_context" in contracts,
"conflicting_gsql_removed":not (ROOT/"gsql").exists(),
"restpp_loader_present":(ROOT/"scripts/load_tigergraph_sample_data_restpp.py").exists()}
report={"status":"passed" if not missing and all(checks.values()) else "failed","missing_files":missing,"checks":checks}
out=ROOT/"docs/part17_5_consolidated_validation.json"; out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(report,indent=2),encoding="utf-8"); print(json.dumps(report,indent=2))
if report["status"]!="passed": raise SystemExit(1)
