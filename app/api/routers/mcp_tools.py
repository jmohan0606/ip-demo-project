from __future__ import annotations

"""Section 11.8 — MCP tool registry endpoints (feature-store + model-serving tool families)."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.mcp import tool_registry
from app.shared.responses import ok

router = APIRouter(prefix="/mcp", tags=["MCP Layer"])


@router.get("/tools")
def tools():
    """The MCP tool catalog (poster shape): families + tool descriptors."""
    return ok(data=tool_registry.catalog())


class InvokeRequest(BaseModel):
    tool: str
    arguments: dict = {}


@router.post("/invoke")
def invoke(request: InvokeRequest):
    """Invoke an MCP tool by name with JSON arguments (the agent-layer call path)."""
    try:
        result = tool_registry.invoke(request.tool, request.arguments)
    except KeyError as exc:
        return ok(data={"error": str(exc), "tool": request.tool})
    return ok(data={"tool": request.tool, "result": result})
