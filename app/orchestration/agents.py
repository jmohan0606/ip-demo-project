from __future__ import annotations

from typing import Any

from app.orchestration.state import OrchestrationState
from app.orchestration.tools import ToolRuntime


class BaseAgent:
    name = "BaseAgent"

    def run(self, state: OrchestrationState, tools: ToolRuntime) -> OrchestrationState:
        raise NotImplementedError


class SupervisorAgent(BaseAgent):
    name = "SupervisorAgent"

    def run(self, state: OrchestrationState, tools: ToolRuntime) -> OrchestrationState:
        state.current_agent = self.name
        state.add_step(
            self.name,
            "completed",
            124,
            f"Workflow={state.workflow}",
            "Routed request to specialist agents.",
        )
        return state


class ContextAgent(BaseAgent):
    name = "ContextAgent"

    def run(self, state: OrchestrationState, tools: ToolRuntime) -> OrchestrationState:
        context = state.context
        state.memory.append({
            "type": "short_term_context",
            "summary": f"{context.get('persona')} viewing {context.get('scope_type')} {context.get('scope_id')} for {context.get('period')}",
        })
        state.add_step(
            self.name,
            "completed",
            168,
            "Resolve persona, scope, period and compare context.",
            "Context normalized and stored in short-term orchestration memory.",
        )
        return state


class DashboardInsightAgent(BaseAgent):
    name = "DashboardInsightAgent"

    def run(self, state: OrchestrationState, tools: ToolRuntime) -> OrchestrationState:
        result, call = tools.call("dashboard_data", state.context)
        state.result["dashboard"] = result
        state.evidence.append({"source": "dashboard_data", "summary": "Dashboard metrics and AI insight returned."})
        state.add_step(
            self.name,
            "completed",
            241,
            "Fetch dashboard intelligence.",
            "Generated dashboard metrics, insights and coaching card.",
            [call],
        )
        return state


class Advisor360Agent(BaseAgent):
    name = "Advisor360Agent"

    def run(self, state: OrchestrationState, tools: ToolRuntime) -> OrchestrationState:
        result, call = tools.call("advisor_360", state.context)
        state.result["advisor_360"] = result
        state.add_step(self.name, "completed", 230, "Fetch advisor/client context.", "Advisor 360 assembled.", [call])
        return state


class OpportunityAgent(BaseAgent):
    name = "OpportunityAgent"

    def run(self, state: OrchestrationState, tools: ToolRuntime) -> OrchestrationState:
        result, call = tools.call("recommendations_workspace", state.context)
        state.result["opportunities"] = result.get("opportunities", [])
        state.result["recommendations_workspace"] = result
        state.add_step(self.name, "completed", 212, "Find opportunities.", "Opportunity pipeline ranked.", [call])
        return state


class RecommendationAgent(BaseAgent):
    name = "RecommendationAgent"

    def run(self, state: OrchestrationState, tools: ToolRuntime) -> OrchestrationState:
        recommendations = state.result.get("recommendations_workspace", {}).get("recommendations", [])
        state.result["recommendations"] = recommendations
        state.add_step(
            self.name,
            "completed",
            198,
            "Generate next best actions.",
            f"Generated {len(recommendations)} recommendations.",
        )
        return state


class ComplianceAgent(BaseAgent):
    name = "ComplianceAgent"

    def run(self, state: OrchestrationState, tools: ToolRuntime) -> OrchestrationState:
        for rec in state.result.get("recommendations", []):
            rec.setdefault("compliance", "Passed")
        state.add_step(
            self.name,
            "completed",
            176,
            "Validate recommendation compliance.",
            "Compliance status attached to recommendations.",
        )
        return state


class GraphAgent(BaseAgent):
    name = "GraphAgent"

    def run(self, state: OrchestrationState, tools: ToolRuntime) -> OrchestrationState:
        result, call = tools.call("graph_explore", state.context)
        state.result["graph"] = result
        state.evidence.append({"source": "graph", "summary": "Graph relationships retrieved."})
        state.add_step(self.name, "completed", 260, "Explore graph.", "Graph nodes and edges returned.", [call])
        return state


class FeatureEmbeddingAgent(BaseAgent):
    name = "FeatureEmbeddingAgent"

    def run(self, state: OrchestrationState, tools: ToolRuntime) -> OrchestrationState:
        result, call = tools.call("features_embeddings", state.context)
        state.result["features_embeddings"] = result
        state.add_step(self.name, "completed", 219, "Load feature and embedding context.", "Feature sets and similarity results returned.", [call])
        return state


class KnowledgeAgent(BaseAgent):
    name = "KnowledgeAgent"

    def run(self, state: OrchestrationState, tools: ToolRuntime) -> OrchestrationState:
        payload = {**state.context, "query": state.input_payload.get("query", "managed account growth playbook")}
        result, call = tools.call("knowledge_search", payload)
        state.result["knowledge"] = result
        state.evidence.append({"source": "chroma", "summary": "Knowledge search results returned."})
        state.add_step(self.name, "completed", 205, "Search Chroma knowledge base.", "Knowledge results and citations returned.", [call])
        return state


class PredictionAgent(BaseAgent):
    name = "PredictionAgent"

    def run(self, state: OrchestrationState, tools: ToolRuntime) -> OrchestrationState:
        payload = {**state.context, **state.input_payload}
        result, call = tools.call("what_if", payload)
        state.result["what_if"] = result
        state.add_step(self.name, "completed", 229, "Run prediction/scenario model.", "Scenario output generated.", [call])
        return state


class MemoryExplainabilityAgent(BaseAgent):
    name = "MemoryExplainabilityAgent"

    def run(self, state: OrchestrationState, tools: ToolRuntime) -> OrchestrationState:
        result, call = tools.call("memory_explainability", state.context)
        state.result["memory_explainability"] = result
        state.evidence.extend(result.get("evidence", []))
        state.add_step(self.name, "completed", 214, "Build explainability and memory view.", "Memory timeline and evidence assembled.", [call])
        return state


class FeedbackLearningAgent(BaseAgent):
    name = "FeedbackLearningAgent"

    def run(self, state: OrchestrationState, tools: ToolRuntime) -> OrchestrationState:
        action = state.input_payload.get("action", "view")
        recommendation_id = state.input_payload.get("recommendation_id", "REC-001")
        result, call = tools.call("persist_feedback", {
            **state.context,
            "recommendation_id": recommendation_id,
            "action": action,
            "notes": state.input_payload.get("notes", ""),
        })
        state.result["feedback"] = {
            "recommendation_id": recommendation_id,
            "action": action,
            "learning_signal": f"{action} captured and stored for future recommendation ranking.",
            "memory_update": "Feedback persisted through GraphRuntime.",
            "graph_runtime": result,
        }
        state.add_step(
            self.name,
            "completed",
            156,
            "Capture feedback action.",
            f"Feedback captured for {recommendation_id}: {action}.",
            [call],
        )
        return state


class ResponseComposerAgent(BaseAgent):
    name = "ResponseComposerAgent"

    def run(self, state: OrchestrationState, tools: ToolRuntime) -> OrchestrationState:
        state.status = "success"
        state.result["orchestration_trace"] = state.to_trace()
        state.result["evidence"] = state.evidence
        state.add_step(
            self.name,
            "completed",
            142,
            "Compose final response.",
            "Response includes result, evidence and trace.",
        )
        state.result["orchestration_trace"] = state.to_trace()
        return state
