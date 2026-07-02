from __future__ import annotations

from app.orchestration.demo_orchestrator import EndToEndDemoOrchestrator, DemoRunResult


class DemoOrchestrationService:
    def run_full_demo(self, advisor_id: str = "ADV0001") -> DemoRunResult:
        return EndToEndDemoOrchestrator().run_full_local_demo(advisor_id)
