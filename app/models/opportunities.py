from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel, Field


class OpportunityType(StrEnum):
    MANAGED_ACCOUNT_EXPANSION = "Managed Account Expansion"
    NNM_GROWTH = "NNM Growth"
    AUM_RETENTION = "AUM Retention"
    AGP_GOAL_RECOVERY = "AGP Goal Recovery"
    CRM_ENGAGEMENT_GAP = "CRM Engagement Gap"
    PEER_BENCHMARK_GAP = "Peer Benchmark Gap"


class OpportunityPriority(StrEnum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class OpportunityStatus(StrEnum):
    OPEN = "Open"
    IN_REVIEW = "In Review"
    ACCEPTED = "Accepted"
    DISMISSED = "Dismissed"
    CONVERTED = "Converted"


class OpportunityRecord(BaseModel):
    opportunity_id: str
    entity_type: str = "Advisor"
    entity_id: str
    household_id: str | None = None
    opportunity_type: OpportunityType
    title: str
    description: str
    score: float
    priority: OpportunityPriority
    status: OpportunityStatus = OpportunityStatus.OPEN
    evidence: list[str] = Field(default_factory=list)
    reasoning_steps: list[str] = Field(default_factory=list)
    feature_snapshot: dict = Field(default_factory=dict)
    prediction_id: str | None = None
    created_ts: datetime = Field(default_factory=datetime.utcnow)


class OpportunityRunRequest(BaseModel):
    entity_id: str | None = None
    write_to_tigergraph: bool = True
    min_score: float = 0.45
    limit: int = 500


class OpportunityRunResult(BaseModel):
    opportunities_created: int
    status: str
    message: str


class OpportunitySearchRequest(BaseModel):
    entity_id: str | None = None
    opportunity_type: OpportunityType | None = None
    priority: OpportunityPriority | None = None
    limit: int = 100
