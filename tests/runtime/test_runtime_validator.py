from app.runtime_validation.runtime_validator import FinalRuntimeValidator


def test_runtime_validator_smoke():
    report = FinalRuntimeValidator(".").run_all()
    assert report.checks_passed >= 10
    assert report.checks_failed == 0
