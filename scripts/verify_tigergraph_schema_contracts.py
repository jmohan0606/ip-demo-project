from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.graph.tigergraph_schema_contracts import REQUIRED_EDGES, REQUIRED_QUERIES, REQUIRED_VERTICES



def main() -> None:
    schema = (ROOT / "gsql/schema/iperform_enterprise_schema.gsql").read_text(encoding="utf-8")
    missing_vertices = [v for v in REQUIRED_VERTICES if f"CREATE VERTEX {v}" not in schema]
    missing_edges = [e for e in REQUIRED_EDGES if f"CREATE DIRECTED EDGE {e}" not in schema]
    missing_queries = [q for q in REQUIRED_QUERIES if not (ROOT / f"gsql/queries/{q}.gsql").exists()]
    report = {
        "status": "passed" if not missing_vertices and not missing_edges and not missing_queries else "failed",
        "missing_vertices": missing_vertices,
        "missing_edges": missing_edges,
        "missing_queries": missing_queries,
        "vertex_count": len(REQUIRED_VERTICES),
        "edge_count": len(REQUIRED_EDGES),
        "query_count": len(REQUIRED_QUERIES),
    }
    out = ROOT / "docs/part_16_2_schema_contract_validation.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
