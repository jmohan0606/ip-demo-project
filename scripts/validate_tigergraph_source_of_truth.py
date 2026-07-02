from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.graph.tigergraph_schema_contracts import GRAPH_NAME, REQUIRED_EDGES, REQUIRED_QUERIES, REQUIRED_VERTICES

TG = ROOT / "tigergraph"
GSQL = ROOT / "gsql"

schema_path = TG / "schema" / "phx_dm_iperform_enterprise_schema.gsql"
schema = schema_path.read_text(encoding="utf-8") if schema_path.exists() else ""

missing_vertices = [v for v in REQUIRED_VERTICES if f"CREATE VERTEX {v}" not in schema]
missing_edges = [e for e in REQUIRED_EDGES if f"CREATE DIRECTED EDGE {e}" not in schema]
missing_queries = [q for q in REQUIRED_QUERIES if not (TG / "queries_v1" / f"{q}.gsql").exists()]
non_prefixed_schema_hits = []
for bad in ["CREATE VERTEX Advisor", "CREATE VERTEX Household", "CREATE DIRECTED EDGE HAS_", "CREATE GRAPH iPerformInsights("]:
    if bad in schema:
        non_prefixed_schema_hits.append(bad)

report = {
    "status": "passed" if not missing_vertices and not missing_edges and not missing_queries and not GSQL.exists() and not non_prefixed_schema_hits else "failed",
    "graph_name": GRAPH_NAME,
    "source_of_truth": "tigergraph/",
    "gsql_folder_exists": GSQL.exists(),
    "missing_vertices": missing_vertices,
    "missing_edges": missing_edges,
    "missing_queries": missing_queries,
    "non_prefixed_schema_hits": non_prefixed_schema_hits,
    "vertex_count": len(REQUIRED_VERTICES),
    "edge_count": len(REQUIRED_EDGES),
    "query_count": len(REQUIRED_QUERIES),
}
out = ROOT / "docs" / "tigergraph_source_of_truth_validation.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
if report["status"] != "passed":
    raise SystemExit(1)
