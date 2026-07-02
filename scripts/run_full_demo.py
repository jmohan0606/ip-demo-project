from __future__ import annotations

from app.services.demo_orchestration_service import DemoOrchestrationService


def main() -> None:
    result = DemoOrchestrationService().run_full_demo("ADV0001")
    print("Full demo run status:", result.status)
    print(result.model_dump())


if __name__ == "__main__":
    main()
