from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

required = [
    "app/graph/tigergraph_mcp_stdio_client.py",
    "app/graph/tigergraph_mcp_adapter.py",
    "app/graph/tigergraph_mcp_query_contracts.py",
    "app/graph/tigergraph_production_runtime.py",
    "scripts/tigergraph_mcp_discover_tools.py",
    "scripts/tigergraph_mcp_official_smoke_test.py",
    "scripts/run_tigergraph_mcp_with_existing_connection.py",
    "docs/TIGERGRAPH_MCP_CORRECTED_SOURCE_OF_TRUTH.md",
]

missing = [f for f in required if not (ROOT / f).exists()]
client_text = (ROOT / "app/graph/tigergraph_mcp_stdio_client.py").read_text(encoding="utf-8")
adapter_text = (ROOT / "app/graph/tigergraph_mcp_adapter.py").read_text(encoding="utf-8")
runtime_text = (ROOT / "app/graph/tigergraph_production_runtime.py").read_text(encoding="utf-8")

checks = {
    "uses_mcp_client_session": "ClientSession" in client_text,
    "uses_stdio_client": "stdio_client" in client_text,
    "discovers_tools": "list_tools" in client_text,
    "calls_session_call_tool": "session.call_tool" in client_text,
    "uses_official_tool_names": "tigergraph__run_installed_query" in client_text,
    "no_fake_custom_client_object": "TigerGraphMCPClient" not in adapter_text,
    "logical_queries_not_mcp_tools": "installed_query_name" in runtime_text and "tigergraph__run_installed_query" in runtime_text,
}

report = {
    "status": "passed" if not missing and all(checks.values()) else "failed",
    "missing_files": missing,
    "checks": checks,
}

out = ROOT / "docs/tigergraph_corrected_source_of_truth_validation.json"
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
if report["status"] != "passed":
    raise SystemExit(1)
