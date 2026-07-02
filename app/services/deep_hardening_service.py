from __future__ import annotations

import json
from pathlib import Path

from app.agents.state.agent_state import AgenticRequest, AgentWorkflowState
from app.agents.workflows.native_langgraph_collaboration import NativeLangGraphCollaborationWorkflow
from app.hardening.audits.chroma_persistence_validator import ChromaPersistenceValidator
from app.hardening.audits.dataset_expansion_auditor import DatasetExpansionAuditor
from app.hardening.audits.mcp_usage_auditor import McpUsageAuditor
from app.hardening.audits.ui_progress_auditor import UiProgressAuditor
from app.hardening.audits.upload_resume_validator import UploadResumeValidator
from app.hardening.scenarios.wealth_scenario_auditor import WealthScenarioAuditor
from app.shared.ids import timestamp_id


class DeepHardeningService:
    def run(self) -> dict:
        results = {}

        # Native LangGraph validation.
        try:
            state = AgentWorkflowState(
                request=AgenticRequest(
                    question="Why is revenue low and what should be done next?",
                    persona="Advisor",
                    scope_type="Advisor",
                    scope_id="ADV0001",
                    requested_capabilities=["prediction", "opportunity", "recommendation"],
                    write_to_tigergraph=False,
                ),
                run_id=timestamp_id("hardening_langgraph"),
            )
            final_state = NativeLangGraphCollaborationWorkflow().run(state)
            results["native_langgraph_collaboration"] = {
                "status": "passed",
                "task_count": len(final_state.tasks),
                "evidence_count": len(final_state.evidence),
                "answer_available": bool(final_state.answer),
            }
        except Exception as exc:
            results["native_langgraph_collaboration"] = {
                "status": "failed",
                "error": str(exc),
            }

        results["chroma_persistence"] = ChromaPersistenceValidator().ensure_real_collection()
        results["mcp_usage_audit"] = McpUsageAuditor(".").audit()
        results["ui_progress_audit"] = UiProgressAuditor(".").audit()
        results["wealth_scenario_audit"] = WealthScenarioAuditor(".").audit()
        results["upload_resume_validation"] = UploadResumeValidator().validate()
        results["dataset_expansion_audit"] = DatasetExpansionAuditor(".").audit()

        failed = []
        for key, value in results.items():
            if value.get("status") not in {"passed", "real_chroma_persistent_collection_ready", "fallback_index_ready_chromadb_unavailable"}:
                # Chroma fallback is still considered not full coverage; mark separately below.
                failed.append(key)

        full_coverage_notes = []
        if results["chroma_persistence"].get("status") != "real_chroma_persistent_collection_ready":
            full_coverage_notes.append("Persistent Chroma/vector collection was not created.")
            failed.append("real_chroma_persistent_collection")

        overall = "passed" if not failed else "failed"
        report = {
            "overall_status": overall,
            "failed_items": failed,
            "full_coverage_notes": full_coverage_notes,
            "results": results,
        }

        out = Path("docs/deep_hardening/deep_runtime_hardening_report.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report
