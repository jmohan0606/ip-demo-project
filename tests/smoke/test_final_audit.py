from app.audit.package_auditor import PackageAuditor


def test_final_audit_runs():
    report = PackageAuditor(".").write_reports()
    assert report["python_compile"]["status"] == "passed"
    assert report["sqlite"]["status"] == "passed"
    assert report["chroma"]["status"] == "passed"
