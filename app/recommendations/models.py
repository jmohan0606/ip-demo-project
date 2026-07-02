from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Opportunity:
    opportunity_id: str
    title: str
    category: str
    score: float
    impact: float
    priority: str
    status: str
    drivers: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Recommendation:
    recommendation_id: str
    opportunity_id: str
    title: str
    action_type: str
    priority: str
    confidence: float
    impact: float
    compliance_status: str
    status: str = "Generated"
    reasoning: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)


@dataclass
class FeedbackEvent:
    feedback_id: str
    recommendation_id: str
    action: str
    notes: str
    learning_signal: str
    score_delta: float
    memory_update: str
