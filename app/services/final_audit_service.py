from __future__ import annotations

from app.audit.package_auditor import PackageAuditor


class FinalAuditService:
    def run_audit(self) -> dict:
        return PackageAuditor(".").write_reports()
