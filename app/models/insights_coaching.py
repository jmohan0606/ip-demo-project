from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel, Field


class InsightScopeType(StrEnum):
    FIRM = "Firm"
    DIVISION = "Division"
    REGION = "Region"
    MARKET = "Market"
    ADVISOR = "Advisor"


class InsightCardType(StrEnum):
    REVENUE = "Revenue Insight"
    AGP = "AGP Coaching Insight"
    OPPORTUNITY = "Opportunity Insight"
    RECOMMENDATION = "Recommendation Insight"
    CRM = "CRM Engagement Insight"
    EXECUTIVE = "Executive Summary"


class CoachingTone(StrEnum):
    EXECUTIVE = "Executive"
    MANAGER = "Manager"
    ADVISOR = "Advisor"


class InsightRequest(BaseModel):
    scope_type: InsightScopeType = InsightScopeType.ADVISOR
    scope_id: str = "ADV0001"
    persona: str = "Advisor"
    time_period: str = "YTD"
    question: str | None = None
    include_ai_generation: bool = True
    write_to_memory: bool = True
    write_to_tigergraph: bool = True


class InsightEvidence(BaseModel):
    source: str
    title: str
    detail: str
    value: float | str | None = None


class InsightCard(BaseModel):
    insight_id: str
    card_type: InsightCardType
    title: str
    summary: str
    severity: str = "Medium"
    confidence: float = 0.80
    evidence: list[InsightEvidence] = Field(default_factory=list)
    reasoning_steps: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)


class CoachingPlan(BaseModel):
    coaching_plan_id: str
    scope_type: InsightScopeType
    scope_id: str
    persona: str
    tone: CoachingTone
    summary: str
    focus_areas: list[str] = Field(default_factory=list)
    next_best_actions: list[str] = Field(default_factory=list)
    manager_review_notes: list[str] = Field(default_factory=list)
    advisor_talk_track: list[str] = Field(default_factory=list)
    confidence: float = 0.80
    created_ts: datetime = Field(default_factory=datetime.utcnow)


class InsightDashboardPayload(BaseModel):
    scope_type: InsightScopeType
    scope_id: str
    persona: str
    time_period: str
    executive_summary: str
    cards: list[InsightCard] = Field(default_factory=list)
    coaching_plan: CoachingPlan | None = None
    context_summary: str | None = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)
