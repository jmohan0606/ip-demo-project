from __future__ import annotations

import json
from app.services.deep_hardening_service import DeepHardeningService


def main() -> None:
    report = DeepHardeningService().run()
    print(json.dumps({
        "overall_status": report["overall_status"],
        "failed_items": report["failed_items"],
        "full_coverage_notes": report["full_coverage_notes"],
    }, indent=2))
    if report["overall_status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
