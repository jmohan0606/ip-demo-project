from __future__ import annotations

from typing import Any

from app.graph import get_graph_runtime
from app.graph.tigergraph_mcp_query_contracts import INSTALLED_QUERY_CONTRACTS, validate_params


class TigerGraphProductionRuntime:
    """Production TigerGraph runtime corrected for official tigergraph-mcp.

    MCP tool names are official `tigergraph__*` names.
    Our business queries are installed GSQL query names.
    Every app query runs through MCP tool `tigergraph__run_installed_query`.
    """

    def __init__(self) -> None:
        self.graph = get_graph_runtime()

    def status(self) -> dict[str, Any]:
        graph_status = self.graph.status()
        return {
            **graph_status,
            "production_data_activation": graph_status["active_mode"] in {"mcp", "rest"},
            "mcp_execution_tool": "tigergraph__run_installed_query",
            "contracts": [
                {
                    "logical_name": contract.logical_name,
                    "installed_query_name": contract.installed_query_name,
                    "mcp_tool_name": "tigergraph__run_installed_query",
                    "required_params": contract.required_params,
                    "description": contract.description,
                }
                for contract in INSTALLED_QUERY_CONTRACTS.values()
            ],
        }

    def run_logical_query(self, logical_name: str, params: dict[str, Any]) -> dict[str, Any]:
        if logical_name not in INSTALLED_QUERY_CONTRACTS:
            return {
                "status": "failed",
                "message": f"Unknown app logical query: {logical_name}",
                "available_queries": sorted(INSTALLED_QUERY_CONTRACTS),
            }

        contract = INSTALLED_QUERY_CONTRACTS[logical_name]
        missing = validate_params(contract, params)
        if missing:
            return {
                "status": "failed",
                "message": f"Missing required params for {logical_name}: {', '.join(missing)}",
                "required_params": contract.required_params,
            }

        result = self.graph.execute_query(contract.installed_query_name, dict(params)).to_dict()
        result["logical_name"] = logical_name
        result["installed_query_name"] = contract.installed_query_name
        result["mcp_tool_name"] = "tigergraph__run_installed_query"
        result["production_data_active"] = result.get("mode") in {"mcp", "rest"}
        return result

    def activate_smoke_test(self) -> dict[str, Any]:
        tests = [
            ("advisor_context", {"advisor_id": "ADV0001"}),
            ("revenue_summary", {"scope_type": "Advisor", "scope_id": "ADV0001", "period": "YTD"}),
            ("advisor_360", {"advisor_id": "ADV0001", "period": "YTD"}),
            ("recommendation_context", {"scope_id": "ADV0001"}),
            ("memory_timeline", {"scope_id": "ADV0001"}),
            ("graph_explorer", {"scope_id": "ADV0001"}),
        ]
        results = [self.run_logical_query(name, params) for name, params in tests]
        return {
            "status": "passed" if all(r.get("status") == "success" for r in results) else "failed",
            "active_mode": self.graph.status()["active_mode"],
            "production_data_active": self.graph.status()["active_mode"] in {"mcp", "rest"},
            "tests": results,
        }


_runtime: TigerGraphProductionRuntime | None = None


def get_tigergraph_production_runtime() -> TigerGraphProductionRuntime:
    global _runtime
    if _runtime is None:
        _runtime = TigerGraphProductionRuntime()
    return _runtime
