from app.services.demo_orchestration_service import DemoOrchestrationService


def test_demo_orchestrator_runs():
    result = DemoOrchestrationService().run_full_demo("ADV0001")
    assert result.status == "completed"
    assert result.summary["insight_cards"] > 0
