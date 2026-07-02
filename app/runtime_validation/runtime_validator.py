from __future__ import annotations

import importlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Callable

from pydantic import BaseModel, Field


class RuntimeCheckResult(BaseModel):
    check_name: str
    status: str
    message: str
    details: dict = Field(default_factory=dict)
    started_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class RuntimeValidationReport(BaseModel):
    status: str
    checks_passed: int
    checks_failed: int
    results: list[RuntimeCheckResult]
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class FinalRuntimeValidator:
    """Runs real app-level validation without requiring external TigerGraph or OpenAI."""

    def __init__(self, root: str | Path = ".") -> None:
        self.root = Path(root)

    def run_all(self) -> RuntimeValidationReport:
        checks: list[tuple[str, Callable[[], dict]]] = [
            ("import_fastapi_app", self.check_fastapi_import),
            ("import_streamlit_app", self.check_streamlit_import),
            ("preloaded_sqlite_read", self.check_sqlite_read),
            ("preloaded_chroma_folder", self.check_chroma_folder),
            ("graph_access_fallback", self.check_graph_access),
            ("agent_registry", self.check_agent_registry),
            ("agentic_workflow", self.check_agentic_workflow),
            ("feature_store_read", self.check_feature_store_read),
            ("prediction_search", self.check_prediction_search),
            ("recommendation_search", self.check_recommendation_search),
            ("feedback_learning_write", self.check_feedback_learning_write),
            ("memory_retrieval", self.check_memory_retrieval),
            ("ai_chat", self.check_ai_chat),
            ("final_audit", self.check_final_audit),
        ]
        results: list[RuntimeCheckResult] = []
        for name, fn in checks:
            started = datetime.utcnow().isoformat()
            try:
                details = fn()
                results.append(RuntimeCheckResult(
                    check_name=name,
                    status="passed",
                    message="Runtime check passed.",
                    details=details,
                    started_at=started,
                    completed_at=datetime.utcnow().isoformat(),
                ))
            except Exception as exc:
                results.append(RuntimeCheckResult(
                    check_name=name,
                    status="failed",
                    message=str(exc),
                    details={},
                    started_at=started,
                    completed_at=datetime.utcnow().isoformat(),
                ))
        passed = sum(1 for r in results if r.status == "passed")
        failed = sum(1 for r in results if r.status == "failed")
        return RuntimeValidationReport(
            status="passed" if failed == 0 else "failed",
            checks_passed=passed,
            checks_failed=failed,
            results=results,
        )

    def write_report(self, output_path: str | Path = "docs/runtime_validation/runtime_validation_report.json") -> dict:
        report = self.run_all()
        path = self.root / output_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report.model_dump(), indent=2), encoding="utf-8")
        return report.model_dump()

    def check_fastapi_import(self) -> dict:
        mod = importlib.import_module("app.api.main")
        app = getattr(mod, "app")
        routes = [getattr(r, "path", "") for r in app.routes]
        assert "/health" in routes or any("health" in r for r in routes)
        assert any("/agentic-ai" in r for r in routes)
        assert any("/graph-access" in r for r in routes)
        return {"route_count": len(routes), "sample_routes": routes[:20]}

    def check_streamlit_import(self) -> dict:
        path = self.root / "app/ui/app_enterprise.py"
        assert path.exists(), "Enterprise Streamlit app missing."
        content = path.read_text(encoding="utf-8", errors="ignore")
        required = ["Agentic AI Console", "Final Audit & Gap Closure", "AI Assistant Chat", "Graph Access Status"]
        missing = [x for x in required if x not in content and x not in (self.root/"app/ui/components/navigation.py").read_text(encoding="utf-8", errors="ignore")]
        assert not missing, f"Missing UI navigation/page references: {missing}"
        return {"app": str(path), "required_pages": required}

    def check_sqlite_read(self) -> dict:
        db = self.root / "data/sqlite/iperform.db"
        assert db.exists(), "Preloaded SQLite DB missing."
        conn = sqlite3.connect(db)
        try:
            tables = ["phx_dm_feature_vector", "phx_dm_local_recommendation", "phx_dm_local_context_memory"]
            counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
            assert all(v > 0 for v in counts.values()), counts
            return {"db_size": db.stat().st_size, "counts": counts}
        finally:
            conn.close()

    def check_chroma_folder(self) -> dict:
        chroma = self.root / "data/chroma"
        assert chroma.exists(), "Chroma folder missing."
        manifest = chroma / "preloaded_chroma_manifest.json"
        index = chroma / "preloaded_knowledge_index.json"
        assert manifest.exists(), "Chroma manifest missing."
        assert index.exists(), "Chroma fallback index missing."
        return {"manifest": json.loads(manifest.read_text(encoding="utf-8")), "index_size": index.stat().st_size}

    def check_graph_access(self) -> dict:
        from app.services.graph_access_service import GraphAccessService
        service = GraphAccessService()
        health = service.health()
        assert health["active_mode"] in {"mcp", "rest", "mock", "unavailable"}
        schema = service.schema()
        assert schema["success"] is True
        return {"health": health, "schema_mode": schema.get("mode")}

    def check_agent_registry(self) -> dict:
        from app.services.agentic_ai_service import AgenticAiService
        agents = AgenticAiService().list_agents()
        names = {a["name"] for a in agents}
        required = {"supervisor", "tigergraph_graph_agent", "recommendation_agent", "ai_assistant_agent"}
        missing = required - names
        assert not missing, f"Missing agents: {missing}"
        return {"agent_count": len(agents), "agents": sorted(names)}

    def check_agentic_workflow(self) -> dict:
        from app.agents.state.agent_state import AgenticRequest
        from app.services.agentic_ai_service import AgenticAiService

        response = AgenticAiService().run(
            AgenticRequest(
                question="Why is my revenue low and what should I do next?",
                persona="Advisor",
                scope_type="Advisor",
                scope_id="ADV0001",
                requested_capabilities=["prediction", "opportunity", "recommendation"],
                write_to_tigergraph=False,
            )
        )
        assert response.answer
        assert response.tasks
        assert response.evidence
        return {"task_count": len(response.tasks), "evidence_count": len(response.evidence), "confidence": response.confidence}

    def check_feature_store_read(self) -> dict:
        from app.services.feature_store_service import FeatureStoreService
        vector = FeatureStoreService().get_vector("Advisor", "ADV0001", "advisor_growth_features")
        assert vector is not None, "Feature vector not found for ADV0001"
        return {"feature_keys": list(vector["features"].keys())[:10]}

    def check_prediction_search(self) -> dict:
        from app.models.predictions import PredictionSearchRequest
        from app.services.prediction_service import PredictionService
        rows = PredictionService().list_predictions(PredictionSearchRequest(entity_id="ADV0001", limit=10))
        assert rows, "No predictions for ADV0001"
        return {"prediction_count": len(rows), "sample": rows[0]}

    def check_recommendation_search(self) -> dict:
        from app.models.recommendations import RecommendationSearchRequest
        from app.services.recommendation_service import RecommendationService
        rows = RecommendationService().list_recommendations(RecommendationSearchRequest(entity_id="ADV0001", limit=10))
        assert rows, "No recommendations for ADV0001"
        return {"recommendation_count": len(rows), "sample_id": rows[0]["recommendation_id"]}

    def check_feedback_learning_write(self) -> dict:
        from app.models.feedback_learning import FeedbackAction, FeedbackActor, FeedbackSubmitRequest, OutcomeType
        from app.models.recommendations import RecommendationSearchRequest
        from app.services.feedback_learning_service import FeedbackLearningService
        from app.services.recommendation_service import RecommendationService

        recs = RecommendationService().list_recommendations(RecommendationSearchRequest(entity_id="ADV0001", limit=1))
        assert recs, "No recommendation available for feedback validation."
        result = FeedbackLearningService().submit_feedback(
            FeedbackSubmitRequest(
                recommendation_id=recs[0]["recommendation_id"],
                actor=FeedbackActor.ADVISOR,
                action=FeedbackAction.ACCEPT,
                reason="Runtime validation feedback.",
                outcome_type=OutcomeType.MEETING_SCHEDULED,
                outcome_value=1,
                outcome_summary="Runtime validation meeting scheduled.",
                write_to_tigergraph=False,
            )
        )
        assert result.learning_signal.learning_signal_id
        return {"feedback_id": result.feedback.feedback_id, "learning_signal_id": result.learning_signal.learning_signal_id}

    def check_memory_retrieval(self) -> dict:
        from app.models.memory import MemoryRetrievalRequest, MemoryScopeType
        from app.services.context_service import ContextService
        package = ContextService().build_context_package(
            MemoryRetrievalRequest(scope_type=MemoryScopeType.ADVISOR, scope_id="ADV0001", limit=5)
        )
        assert package.evidence_count > 0, "No context memory for ADV0001"
        return {"evidence_count": package.evidence_count}

    def check_ai_chat(self) -> dict:
        from app.models.ai_chat import ChatPersona, ChatRequest, ChatScopeType
        from app.services.ai_assistant_chat_service import AiAssistantChatService
        response = AiAssistantChatService().ask(
            ChatRequest(
                question="What should I do next?",
                persona=ChatPersona.ADVISOR,
                scope_type=ChatScopeType.ADVISOR,
                scope_id="ADV0001",
                include_knowledge=False,
                write_to_tigergraph=False,
            )
        )
        assert response.answer
        assert response.context_items
        return {"conversation_id": response.conversation_id, "context_items": len(response.context_items)}

    def check_final_audit(self) -> dict:
        from app.audit.package_auditor import PackageAuditor
        report = PackageAuditor(".").write_reports()
        assert report["summary"]["overall_status"] == "passed", report["summary"]
        return report["summary"]
