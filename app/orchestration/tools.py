from app.llm import get_llm_runtime
from app.memory import get_memory_runtime
from app.recommendations import get_recommendation_runtime
from app.features import get_feature_runtime
from __future__ import annotations

from typing import Any

from app.graph import get_graph_runtime
from app.orchestration.state import ToolCallRecord
from app.services.ui_integrated_service import get_dashboard_data, run_what_if_simulation
from app.services.ui_integrated_expanded_service import (
    get_advisor_360_data,
    get_features_embeddings_data,
    get_graph_explorer_data,
    get_memory_explainability_data,
    get_recommendations_workspace_data,
    search_knowledge,
)


class ToolRuntime:
    """Agent tool facade with TigerGraph MCP-first graph runtime.

    Graph-related calls go through GraphRuntime:
    MCP -> REST -> mock.

    Non-graph demo calls remain local service calls until their real service
    implementations are wired in later parts.
    """

    def __init__(self) -> None:
        self.graph = get_graph_runtime()
        self.features = get_feature_runtime()
        self.recommendations = get_recommendation_runtime()
        self.memory_runtime = get_memory_runtime()
        self.llm = get_llm_runtime()

    def call(self, tool_name: str, payload: dict[str, Any]) -> tuple[Any, ToolCallRecord]:
        graph_tool = False

        if tool_name == "dashboard_data":
            result = get_dashboard_data(payload)

        elif tool_name == "advisor_360":
            result = get_advisor_360_data(payload)
            graph_result = self.graph.execute_query("get_advisor_context", {"advisor_id": payload.get("scope_id", "ADV0001")})
            result["graph_runtime"] = graph_result.to_dict()
            graph_tool = True

        elif tool_name == "recommendations_workspace":
            local = get_recommendations_workspace_data(payload)
            result = {**local, "recommendation_runtime": self.recommendations.generate(payload)}

        elif tool_name == "graph_explore":
            local = get_graph_explorer_data(payload)
            graph_result = self.graph.execute_query("get_advisor_context", {"advisor_id": payload.get("scope_id", "ADV0001")})
            result = {**local, "graph_runtime": graph_result.to_dict()}
            graph_tool = True

        elif tool_name == "features_embeddings":
            local = get_features_embeddings_data(payload)
            result = {**local, "feature_runtime": self.features.get_feature_summary(payload), "similarity_runtime": self.features.similarity_search(payload)}

        elif tool_name == "memory_explainability":
            result = get_memory_explainability_data(payload)
            context_packet = self.memory_runtime.build_context_packet(
                payload,
                payload.get("query", "advisor revenue decline managed account recommendation"),
                max_tokens=900,
            )
            result["context_packet"] = context_packet
            graph_tool = True

        elif tool_name == "knowledge_search":
            result = search_knowledge(payload)

        elif tool_name == "what_if":
            result = run_what_if_simulation(payload)
            result["prediction_runtime"] = self.features.predict(payload, payload)
            scenario_id = f"SCN-{payload.get('scope_id', 'ADV0001')}"
            scenario_result = self.graph.upsert_vertex("Scenario", scenario_id, {
                "scenario_id": scenario_id,
                "scope_id": payload.get("scope_id"),
                "meeting_increase_pct": payload.get("meeting_increase_pct", 0),
                "managed_revenue_shift_pct": payload.get("managed_revenue_shift_pct", 0),
            })
            result["graph_runtime"] = scenario_result.to_dict()
            graph_tool = True

        elif tool_name == "persist_feedback":
            result = self.graph.persist_recommendation_feedback(payload).to_dict()
            graph_tool = True

        else:
            result = {
                "tool_name": tool_name,
                "status": "mock_result",
                "payload_keys": sorted(payload.keys()),
            }

        mode = result.get("graph_runtime", {}).get("mode") if isinstance(result, dict) else None
        return result, ToolCallRecord(
            tool_name=tool_name if not graph_tool else f"{tool_name} via GraphRuntime({mode or 'mixed'})",
            status="success",
            duration_ms=90 + len(tool_name) * 3,
            input_summary=f"Payload keys: {', '.join(sorted(payload.keys()))}",
            output_summary=f"Returned {type(result).__name__}",
        )
