from __future__ import annotations

from typing import Any

from app.graph.mock_graph_store import MockGraphStore
from app.graph.models import GraphRuntimeResult
from app.graph.tigergraph_mcp_adapter import TigerGraphMcpAdapter
from app.graph.tigergraph_rest_adapter import TigerGraphRestAdapter


class GraphRuntime:
    """MCP-first graph runtime.

    Order:
    1. TigerGraph MCP
    2. TigerGraph REST
    3. MockGraphStore

    This keeps local demo working while making TigerGraph MCP the first option
    once configured.
    """

    def __init__(self) -> None:
        self.mcp = TigerGraphMcpAdapter()
        self.rest = TigerGraphRestAdapter()
        self.mock = MockGraphStore()

    def status(self) -> dict[str, Any]:
        mcp_available = self.mcp.is_available()
        tool_result = self.mcp.list_tools() if mcp_available else {"tools": [], "status": "not_available", "message": self.mcp.last_error}
        return {
            "strategy": "official_tigergraph_mcp_stdio_first",
            "mcp_available": mcp_available,
            "mcp_tool_count": len(tool_result.get("tools", [])),
            "mcp_tools": [tool.get("name") for tool in tool_result.get("tools", [])],
            "mcp_last_error": self.mcp.last_error,
            "rest_available": self.rest.is_available(),
            "rest_status": self.rest.status() if hasattr(self.rest, "status") else {},
            "mock_available": True,
            "active_mode": "mcp" if mcp_available else "rest" if self.rest.is_available() else "mock",
        }

    def _execute_with_fallback(self, operation: str, method: str, *args, **kwargs) -> GraphRuntimeResult:
        traces: list[dict[str, Any]] = []

        for mode, adapter in [("mcp", self.mcp), ("rest", self.rest), ("mock", self.mock)]:
            try:
                if mode != "mock" and hasattr(adapter, "is_available") and not adapter.is_available():
                    traces.append({"mode": mode, "status": "skipped", "message": "not available"})
                    continue
                result = getattr(adapter, method)(*args, **kwargs)
                traces.append({"mode": mode, "status": "success"})
                return GraphRuntimeResult(
                    status="success",
                    mode=mode,
                    operation=operation,
                    data=result,
                    fallback_used=mode != "mcp",
                    message=f"{operation} completed using {mode}",
                    tool_trace=traces,
                )
            except Exception as exc:
                traces.append({"mode": mode, "status": "failed", "message": str(exc)})

        return GraphRuntimeResult(
            status="failed",
            mode="none",
            operation=operation,
            data=None,
            fallback_used=True,
            message=f"{operation} failed across MCP, REST and mock",
            tool_trace=traces,
        )

    def execute_query(self, query_name: str, params: dict[str, Any]) -> GraphRuntimeResult:
        return self._execute_with_fallback("execute_query", "execute_query", query_name, params)

    def upsert_vertex(self, vertex_type: str, vertex_id: str, attributes: dict[str, Any]) -> GraphRuntimeResult:
        return self._execute_with_fallback("upsert_vertex", "upsert_vertex", vertex_type, vertex_id, attributes)

    def upsert_edge(
        self,
        edge_type: str,
        from_type: str,
        from_id: str,
        to_type: str,
        to_id: str,
        attributes: dict[str, Any],
    ) -> GraphRuntimeResult:
        return self._execute_with_fallback("upsert_edge", "upsert_edge", edge_type, from_type, from_id, to_type, to_id, attributes)

    def persist_recommendation_feedback(self, payload: dict[str, Any]) -> GraphRuntimeResult:
        rec_id = payload.get("recommendation_id", "REC-001")
        action = payload.get("action", "accept")
        feedback_id = f"FDB-{rec_id}-{action}".replace(" ", "_")
        vertex = self.upsert_vertex("Feedback", feedback_id, {
            "feedback_id": feedback_id,
            "recommendation_id": rec_id,
            "action": action,
            "notes": payload.get("notes", ""),
            "created_at": payload.get("created_at", ""),
        })
        edge = self.upsert_edge("HAS_FEEDBACK", "Recommendation", rec_id, "Feedback", feedback_id, {"action": action})
        return GraphRuntimeResult(
            status="success" if vertex.status == "success" and edge.status == "success" else "partial",
            mode=edge.mode,
            operation="persist_recommendation_feedback",
            data={"vertex": vertex.to_dict(), "edge": edge.to_dict()},
            fallback_used=vertex.fallback_used or edge.fallback_used,
            message="Recommendation feedback persisted through graph runtime",
            tool_trace=vertex.tool_trace + edge.tool_trace,
        )

    def persist_memory_event(self, payload: dict[str, Any]) -> GraphRuntimeResult:
        memory_id = payload.get("memory_id", "MEM-DEMO")
        return self.upsert_vertex("Memory", memory_id, payload)

    def persist_agent_trace(self, trace: dict[str, Any]) -> GraphRuntimeResult:
        execution_id = trace.get("execution_id", "EXEC-DEMO")
        return self.upsert_vertex("AgentExecution", execution_id, trace)


_graph_runtime: GraphRuntime | None = None


def get_graph_runtime() -> GraphRuntime:
    global _graph_runtime
    if _graph_runtime is None:
        _graph_runtime = GraphRuntime()
    return _graph_runtime
