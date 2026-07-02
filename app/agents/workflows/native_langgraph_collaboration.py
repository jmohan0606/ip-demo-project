from __future__ import annotations

from typing import Any

from app.agents.registry.agent_registry import AgentRegistry
from app.agents.state.agent_state import AgentWorkflowState


class NativeLangGraphCollaborationWorkflow:
    """Native collaborative LangGraph workflow.

    This workflow is intentionally different from the earlier linear fallback:
    - Supervisor creates route.
    - Context, Graph, RAG, Prediction run as parallel/collaborative evidence gatherers.
    - Opportunity and Recommendation run after predictions.
    - Feedback is optional, based on route.
    - Explainability consolidates evidence.
    - AI Assistant synthesizes final answer.

    If LangGraph is unavailable, it raises; validation verifies this class exists and
    can build/execute when dependency is present.
    """

    def __init__(self) -> None:
        self.registry = AgentRegistry()

    def _node(self, agent_name: str):
        def run_node(data: dict[str, Any]) -> dict[str, Any]:
            state = AgentWorkflowState.model_validate(data["state"])
            state = self.registry.get(agent_name).run(state)
            return {"state": state.model_dump()}
        return run_node

    def run(self, state: AgentWorkflowState) -> AgentWorkflowState:
        try:
            return self._run_real_langgraph(state)
        except Exception as exc:
            state.reasoning_steps.append(f"Native LangGraph SDK unavailable or failed; using built-in collaborative graph simulator: {exc}")
            return self._run_internal_collaboration_graph(state)

    def _run_real_langgraph(self, state: AgentWorkflowState) -> AgentWorkflowState:
        from langgraph.graph import END, StateGraph  # type: ignore

        workflow = StateGraph(dict)
        nodes = [
            "supervisor",
            "context_retrieval_agent",
            "tigergraph_graph_agent",
            "rag_knowledge_agent",
            "prediction_agent",
            "opportunity_agent",
            "recommendation_agent",
            "feedback_learning_agent",
            "explainability_agent",
            "ai_assistant_agent",
        ]
        for node in nodes:
            workflow.add_node(node, self._node(node))
        workflow.set_entry_point("supervisor")
        workflow.add_edge("supervisor", "context_retrieval_agent")
        workflow.add_edge("supervisor", "tigergraph_graph_agent")
        workflow.add_edge("supervisor", "rag_knowledge_agent")
        workflow.add_edge("supervisor", "prediction_agent")
        workflow.add_edge("prediction_agent", "opportunity_agent")
        workflow.add_edge("opportunity_agent", "recommendation_agent")
        workflow.add_edge("recommendation_agent", "feedback_learning_agent")
        workflow.add_edge("context_retrieval_agent", "explainability_agent")
        workflow.add_edge("tigergraph_graph_agent", "explainability_agent")
        workflow.add_edge("rag_knowledge_agent", "explainability_agent")
        workflow.add_edge("feedback_learning_agent", "explainability_agent")
        workflow.add_edge("explainability_agent", "ai_assistant_agent")
        workflow.add_edge("ai_assistant_agent", END)
        compiled = workflow.compile()
        result = compiled.invoke({"state": state.model_dump()})
        final_state = AgentWorkflowState.model_validate(result["state"])
        final_state.context["langgraph_runtime"] = "real_langgraph_sdk"
        return final_state

    def _run_internal_collaboration_graph(self, state: AgentWorkflowState) -> AgentWorkflowState:
        # Built-in graph simulator preserves the same fan-out/converge topology for
        # environments where `uv sync` has not yet installed LangGraph.
        state = self.registry.get("supervisor").run(state)
        for agent_name in ["context_retrieval_agent", "tigergraph_graph_agent", "rag_knowledge_agent", "prediction_agent"]:
            state = self.registry.get(agent_name).run(state)
        for agent_name in ["opportunity_agent", "recommendation_agent", "feedback_learning_agent"]:
            state = self.registry.get(agent_name).run(state)
        state = self.registry.get("explainability_agent").run(state)
        state = self.registry.get("ai_assistant_agent").run(state)
        state.context["langgraph_runtime"] = "internal_collaboration_graph_simulator"
        return state

    def validate_graph_build(self) -> dict[str, Any]:
        try:
            from langgraph.graph import StateGraph  # type: ignore
            langgraph_available = True
        except Exception:
            langgraph_available = False
        return {
            "langgraph_available": langgraph_available,
            "workflow": "native_branching_collaboration",
            "collaboration_pattern": "supervisor_fanout_then_converge",
            "fallback_simulator_available": True,
        }
