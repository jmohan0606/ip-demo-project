from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.graph.tigergraph_mcp_adapter import TigerGraphMcpAdapter


def main() -> None:
    adapter = TigerGraphMcpAdapter()
    report = {
        "mcp_available": adapter.is_available(),
        "last_error": adapter.last_error,
        "tools": adapter.list_tools(),
        "list_connections": adapter.list_connections(),
    }
    if report["mcp_available"]:
        report["list_graphs"] = adapter.mapper.call("list_graphs", {})
        report["schema"] = adapter.get_graph_schema()
    else:
        report["list_graphs"] = {"status": "skipped"}
        report["schema"] = {"status": "skipped"}

    out = ROOT / "docs/tigergraph_mcp_official_smoke_test_report.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["mcp_available"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
