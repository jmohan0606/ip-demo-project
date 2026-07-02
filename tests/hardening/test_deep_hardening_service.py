from app.services.deep_hardening_service import DeepHardeningService


def test_deep_hardening_service_runs():
    report = DeepHardeningService().run()
    assert "overall_status" in report
    assert "results" in report
