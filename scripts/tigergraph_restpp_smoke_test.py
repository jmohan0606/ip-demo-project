from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.graph.tigergraph_rest_adapter import TigerGraphRestAdapter


def main() -> None:
    adapter = TigerGraphRestAdapter()
    report = {
        "status": adapter.status(),
        "ping": adapter.ping(),
    }

    if adapter.is_available():
        try:
            report["query_test"] = adapter.execute_query("get_advisor_context", {"advisor_id": "ADV0001"})
        except Exception as exc:
            report["query_test"] = {"status": "failed", "error": str(exc)}

    out = ROOT / "docs/tigergraph_restpp_smoke_test_report.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))

    if report["status"]["enabled"] and report["ping"].get("status") != "success":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
