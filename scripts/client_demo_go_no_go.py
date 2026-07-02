from __future__ import annotations

import json
from pathlib import Path

from app.runtime_validation.runtime_validator import FinalRuntimeValidator


def main() -> None:
    report = FinalRuntimeValidator(".").write_report("docs/runtime_validation/client_demo_go_no_go_report.json")
    go = report["status"] == "passed"
    result = {
        "decision": "GO" if go else "NO_GO",
        "checks_passed": report["checks_passed"],
        "checks_failed": report["checks_failed"],
        "report": "docs/runtime_validation/client_demo_go_no_go_report.json",
    }
    print(json.dumps(result, indent=2))
    if not go:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
