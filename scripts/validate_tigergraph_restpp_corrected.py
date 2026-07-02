from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
required = [
    "app/graph/tigergraph_rest_adapter.py",
    "scripts/tigergraph_restpp_smoke_test.py",
    "docs/TIGERGRAPH_RESTPP_CORRECTED_AUDIT.md",
    "docs/LAST_MILE_INTEGRATION_AUDIT.md",
]
missing = [f for f in required if not (ROOT / f).exists()]
text = (ROOT / "app/graph/tigergraph_rest_adapter.py").read_text(encoding="utf-8")
checks = {
    "uses_restpp_base_url": "TIGERGRAPH_RESTPP_URL" in text and "TG_RESTPP_PORT" in text,
    "installed_query_endpoint": "/query/{graph}/{query_name}" in text,
    "graph_upsert_endpoint": "/graph/{self.graph_name}" in text,
    "supports_jwt_and_token": "TG_JWT_TOKEN" in text and "TG_API_TOKEN" in text,
    "has_ping": "def ping" in text,
    "supports_get_post_query": "TIGERGRAPH_REST_QUERY_METHOD" in text,
}
report = {
    "status": "passed" if not missing and all(checks.values()) else "failed",
    "missing_files": missing,
    "checks": checks,
}
out = ROOT / "docs/tigergraph_restpp_corrected_validation.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
if report["status"] != "passed":
    raise SystemExit(1)
