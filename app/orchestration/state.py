from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass
class ToolCallRecord:
    tool_name: str
    status: str
    duration_ms: int
    input_summary: str
    output_summary: str


@dataclass
class AgentStepRecord:
    agent_name: str
    status: str
    duration_ms: int
    input_summary: str
    output_summary: str
    tool_calls: list[ToolCallRecord] = field(default_factory=list)


@dataclass
class OrchestrationState:
    workflow: str
    context: dict[str, Any]
    input_payload: dict[str, Any]
    execution_id: str = field(default_factory=lambda: f"EXEC-{uuid4().hex[:10].upper()}")
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    status: str = "running"
    current_agent: str | None = None
    memory: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    result: dict[str, Any] = field(default_factory=dict)
    steps: list[AgentStepRecord] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def add_step(
        self,
        agent_name: str,
        status: str,
        duration_ms: int,
        input_summary: str,
        output_summary: str,
        tool_calls: list[ToolCallRecord] | None = None,
    ) -> None:
        self.steps.append(
            AgentStepRecord(
                agent_name=agent_name,
                status=status,
                duration_ms=duration_ms,
                input_summary=input_summary,
                output_summary=output_summary,
                tool_calls=tool_calls or [],
            )
        )

    def to_trace(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "workflow": self.workflow,
            "status": self.status,
            "started_at": self.started_at,
            "agents": [
                {
                    "agent_name": step.agent_name,
                    "status": step.status,
                    "duration_ms": step.duration_ms,
                    "input": step.input_summary,
                    "output": step.output_summary,
                    "tool_calls": [
                        {
                            "tool_name": call.tool_name,
                            "status": call.status,
                            "duration_ms": call.duration_ms,
                            "input_summary": call.input_summary,
                            "output_summary": call.output_summary,
                        }
                        for call in step.tool_calls
                    ],
                }
                for step in self.steps
            ],
            "errors": self.errors,
        }
