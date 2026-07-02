from __future__ import annotations
from app.ai.adapters.adapter_factory import ModelAdapterFactory
from app.models.enums import AdapterProvider
from app.services.runtime_status_service import RuntimeStatusService

def main() -> None:
    adapter = ModelAdapterFactory.create(AdapterProvider.MOCK)
    assert adapter.generate_json("test")["source"] == "mock_adapter"
    report = RuntimeStatusService().get_health_report()
    assert report.application == "iPerform Insights & Coaching"
    assert report.graph_name == "iperform_insights_coaching_demo"
    assert report.schema_prefix == "phx_dm_"
    print("Part 11.0.2 validation passed.")
    print(f"Overall runtime status: {report.overall_status}")

if __name__ == "__main__":
    main()
