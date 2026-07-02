from app.models.enums import RuntimeComponentStatus
from app.services.runtime_status_service import RuntimeStatusService

def test_runtime_status_report_builds():
    report = RuntimeStatusService().get_health_report()
    assert report.application == "iPerform Insights & Coaching"
    assert report.graph_name == "iperform_insights_coaching_demo"
    assert report.schema_prefix == "phx_dm_"
    assert report.overall_status in {RuntimeComponentStatus.HEALTHY, RuntimeComponentStatus.DEGRADED, RuntimeComponentStatus.ERROR}
    assert len(report.components) >= 3
