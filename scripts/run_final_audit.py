from __future__ import annotations

import json

from app.audit.package_auditor import PackageAuditor


def main() -> None:
    report = PackageAuditor(".").write_reports()
    print("Final audit complete.")
    print(json.dumps(report["summary"], indent=2))
    if report["summary"]["overall_status"] != "passed":
        print("Review needed. See docs/final_audit/final_audit_report.json")


if __name__ == "__main__":
    main()
