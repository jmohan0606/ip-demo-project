from __future__ import annotations

import json
from pathlib import Path

from app.services.deep_hardening_service import DeepHardeningService
from app.runtime_validation.runtime_validator import FinalRuntimeValidator


def main() -> None:
    runtime = FinalRuntimeValidator(".").write_report("docs/runtime_validation/no_partial_runtime_report.json")
    hardening = DeepHardeningService().run()

    result = {
        "runtime_status": runtime["status"],
        "deep_hardening_status": hardening["overall_status"],
        "runtime_failed": runtime["checks_failed"],
        "deep_hardening_failed_items": hardening["failed_items"],
        "full_coverage_notes": hardening["full_coverage_notes"],
        "decision": "FULLY_COVERED" if runtime["status"] == "passed" and hardening["overall_status"] == "passed" else "NOT_FULLY_COVERED",
    }
    Path("docs/deep_hardening/no_partial_coverage_report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    if result["decision"] != "FULLY_COVERED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
