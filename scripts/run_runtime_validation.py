from __future__ import annotations

import json

from app.runtime_validation.runtime_validator import FinalRuntimeValidator


def main() -> None:
    report = FinalRuntimeValidator(".").write_report()
    print(json.dumps({
        "status": report["status"],
        "checks_passed": report["checks_passed"],
        "checks_failed": report["checks_failed"],
    }, indent=2))
    if report["status"] != "passed":
        print("Runtime validation failed. See docs/runtime_validation/runtime_validation_report.json")
        for r in report["results"]:
            if r["status"] != "passed":
                print(f"- {r['check_name']}: {r['message']}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
