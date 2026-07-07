"""Single, isolated home for all native-LangGraph graph construction.

WHY THIS MODULE EXISTS
----------------------
The client (JPMC) runs LangGraph through SmartSDK, which re-exports the LangGraph symbols under
`smart_sdk.ext.langgraph` — "there is no need to import from langgraph directly"
(SMARTSDK_REFERENCE.md §4). Graph-construction signatures are IDENTICAL; only the import paths
change. By keeping every native-LangGraph import in this ONE module, the SmartSDK swap on the
client machine is a localized, low-risk edit (this file only), not a hunt across the codebase.

SMARTSDK SWAP — the exact remapping (confirmed from SMARTSDK_REFERENCE.md §4-5).
Replace the ACTIVE import block below with the SmartSDK block. Nothing else in this file changes.

    # ---- NATIVE LANGGRAPH (this build, local) — ACTIVE ----
    from langgraph.graph import END, StateGraph
    # ToolNode / InMemorySaver only needed once tool nodes/checkpointing are used:
    # from langgraph.prebuilt import ToolNode
    # from langgraph.checkpoint.memory import InMemorySaver

    # ---- SMARTSDK (client env) — SWAP TO THIS ----
    # from smart_sdk.ext.langgraph.graph.state import StateGraph
    # from smart_sdk.ext.langgraph import (
    #     ToolNode, InMemorySaver, BaseState, HumanMessage,
    #     END, CompiledStateGraph, Checkpointer, Command,
    #     StreamWriter, interrupt, BaseStore, CheckpointMetadata,
    #     ErrorCode, create_error_message,
    # )
    # from smart_sdk.ext.langgraph.adapter._adapter import LangGraphAgent

Remapping notes (all confirmed):
  * StateGraph / add_node / add_edge / set_entry_point / set_finish_point /
    add_conditional_edges / compile  → signatures UNCHANGED.
  * ToolNode: constructor kwarg `core=` is DEPRECATED — use `tools=` (SMARTSDK_REFERENCE.md §4).
  * Execution: instead of `.compile().invoke(...)`, the SmartSDK-idiomatic path wraps the compiled
    graph in `LangGraphAgent(name=..., description=..., core=compiled_graph)` and runs it via
    `Runner(app_name, session_id).run_async(user_id, new_message)` (SMARTSDK_REFERENCE.md §5).
    The plain `.invoke(...)` used here still works, so the swap can be done in two steps: (1) flip
    the imports (drop-in), then (2) optionally move to Runner for telemetry/eval integration.

This build uses only StateGraph + add_node + add_edge + set_entry_point + END, so step (1) alone
is sufficient for the client env; step (2) is optional (telemetry/eval).
"""

from __future__ import annotations

from typing import Callable


def build_and_run_linear_graph(
    route_plan: list[str],
    node_factory: Callable[[str], Callable[[dict], dict]],
    initial_state: dict,
) -> dict:
    """Build a linear LangGraph over `route_plan` (node i → node i+1 → … → END) and run it.

    `node_factory(agent_name)` returns the node callable for that step; `initial_state` is the
    dict passed to `.invoke()`. Returns the final state dict. This is the ONLY place a LangGraph
    graph is constructed in the app — see the module docstring for the SmartSDK swap.
    """
    # ---- NATIVE LANGGRAPH (this build, local) — ACTIVE ----
    from langgraph.graph import END, StateGraph

    workflow = StateGraph(dict)
    for agent_name in route_plan:
        workflow.add_node(agent_name, node_factory(agent_name))
    for idx, agent_name in enumerate(route_plan):
        if idx == 0:
            workflow.set_entry_point(agent_name)
        next_node = route_plan[idx + 1] if idx < len(route_plan) - 1 else END
        workflow.add_edge(agent_name, next_node)
    return workflow.compile().invoke(initial_state)
