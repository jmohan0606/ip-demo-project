from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.graph.tigergraph_mcp_stdio_client import TigerGraphMcpStdioClient


def main() -> None:
    client = TigerGraphMcpStdioClient()
    tools = client.list_tools()
    report = {
        "status": "passed" if tools else "failed",
        "tool_count": len(tools),
        "tool_names": [tool["name"] for tool in tools],
        "tools": tools,
    }
    out = ROOT / "docs/tigergraph_mcp_tool_discovery_report.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not tools:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
