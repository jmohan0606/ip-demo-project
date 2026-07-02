from __future__ import annotations

from pathlib import Path

from app.services.demo_orchestration_service import DemoOrchestrationService


def main() -> None:
    required = [
        "app/api/main.py",
        "app/ui/app_enterprise.py",
        "app/orchestration/demo_orchestrator.py",
        "tigergraph/schema/01_vertices.gsql",
        "tigergraph/sample_data/demo_data_manifest.json",
    ]
    for file in required:
        assert Path(file).exists(), f"Missing required artifact: {file}"

    result = DemoOrchestrationService().run_full_demo("ADV0001")
    assert result.status == "completed", result.model_dump()
    assert result.summary["predictions"] > 0
    assert result.summary["recommendations"] > 0
    assert result.summary["insight_cards"] > 0

    print("Final end-to-end demo validation passed.")
    print(result.summary)


if __name__ == "__main__":
    main()
