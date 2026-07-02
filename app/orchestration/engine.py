from __future__ import annotations

from typing import Any

from app.orchestration.agents import (
    Advisor360Agent,
    ComplianceAgent,
    ContextAgent,
    DashboardInsightAgent,
    FeatureEmbeddingAgent,
    FeedbackLearningAgent,
    GraphAgent,
    KnowledgeAgent,
    MemoryExplainabilityAgent,
    OpportunityAgent,
    PredictionAgent,
    RecommendationAgent,
    ResponseComposerAgent,
    SupervisorAgent,
)
from app.orchestration.state import OrchestrationState
from app.orchestration.tools import ToolRuntime


class OrchestrationEngine:
    def __init__(self) -> None:
        self.tools = ToolRuntime()

    def _workflow_agents(self, workflow: str):
        if workflow == "dashboard":
            return [SupervisorAgent(), ContextAgent(), DashboardInsightAgent(), OpportunityAgent(), RecommendationAgent(), MemoryExplainabilityAgent(), ResponseComposerAgent()]
        if workflow == "advisor_360":
            return [SupervisorAgent(), ContextAgent(), Advisor360Agent(), GraphAgent(), MemoryExplainabilityAgent(), ResponseComposerAgent()]
        if workflow == "recommendations":
            return [SupervisorAgent(), ContextAgent(), OpportunityAgent(), RecommendationAgent(), ComplianceAgent(), MemoryExplainabilityAgent(), ResponseComposerAgent()]
        if workflow == "what_if":
            return [SupervisorAgent(), ContextAgent(), FeatureEmbeddingAgent(), PredictionAgent(), RecommendationAgent(), MemoryExplainabilityAgent(), ResponseComposerAgent()]
        if workflow == "graph":
            return [SupervisorAgent(), ContextAgent(), GraphAgent(), MemoryExplainabilityAgent(), ResponseComposerAgent()]
        if workflow == "features_embeddings":
            return [SupervisorAgent(), ContextAgent(), FeatureEmbeddingAgent(), ResponseComposerAgent()]
        if workflow == "knowledge":
            return [SupervisorAgent(), ContextAgent(), KnowledgeAgent(), ResponseComposerAgent()]
        if workflow == "memory_explainability":
            return [SupervisorAgent(), ContextAgent(), MemoryExplainabilityAgent(), ResponseComposerAgent()]
        if workflow == "feedback":
            return [SupervisorAgent(), ContextAgent(), FeedbackLearningAgent(), MemoryExplainabilityAgent(), ResponseComposerAgent()]
        return [SupervisorAgent(), ContextAgent(), DashboardInsightAgent(), ResponseComposerAgent()]

    def run(self, workflow: str, context: dict[str, Any], input_payload: dict[str, Any] | None = None) -> dict[str, Any]:
        state = OrchestrationState(workflow=workflow, context=context, input_payload=input_payload or {})
        try:
            for agent in self._workflow_agents(workflow):
                state = agent.run(state, self.tools)
            state.status = "success"
        except Exception as exc:
            state.status = "failed"
            state.errors.append(str(exc))
        state.result["orchestration_trace"] = state.to_trace()
        state.result.setdefault("evidence", state.evidence)
        return state.result


_engine: OrchestrationEngine | None = None


def get_orchestration_engine() -> OrchestrationEngine:
    global _engine
    if _engine is None:
        _engine = OrchestrationEngine()
    return _engine
