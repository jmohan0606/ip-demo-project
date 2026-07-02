from app.hardening.scenarios.wealth_scenario_auditor import WealthScenarioAuditor


def test_wealth_scenario_audit_runs():
    report = WealthScenarioAuditor(".").audit()
    assert "status" in report
    assert "files" in report
