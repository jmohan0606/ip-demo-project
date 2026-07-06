from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel, Field


class RecommendationType(StrEnum):
    MANAGED_ACCOUNT_REVIEW = "Managed Account Review"
    NNM_GROWTH_ACTION = "NNM Growth Action"
    AUM_RETENTION_ACTION = "AUM Retention Action"
    AGP_COACHING_ACTION = "AGP Coaching Action"
    CRM_ENGAGEMENT_ACTION = "CRM Engagement Action"
    PEER_BENCHMARK_ACTION = "Peer Benchmark Action"


class RecommendationStatus(StrEnum):
    GENERATED = "generated"        # legacy synonym of OPEN (old SQLite rows)
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    IGNORED = "ignored"
    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"    # NEW (Section 13.1)
    MODIFIED = "modified"          # NEW (Section 13.1)


class ComplianceStatus(StrEnum):
    PASSED = "passed"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"


class RecommendationRecord(BaseModel):
    recommendation_id: str
    entity_type: str = "Advisor"
    entity_id: str
    household_id: str | None = None
    opportunity_id: str | None = None
    prediction_id: str | None = None
    playbook_id: str | None = None
    recommendation_type: RecommendationType
    title: str
    action_text: str
    rationale: str
    score: float
    confidence: float
    status: RecommendationStatus = RecommendationStatus.GENERATED
    compliance_status: ComplianceStatus = ComplianceStatus.PASSED
    supporting_documents: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    reasoning_steps: list[str] = Field(default_factory=list)
    created_ts: datetime = Field(default_factory=datetime.utcnow)
    updated_ts: datetime = Field(default_factory=datetime.utcnow)


class RecommendationRunRequest(BaseModel):
    entity_id: str | None = None
    write_to_tigergraph: bool = True
    min_opportunity_score: float = 0.45
    limit: int = 500


class RecommendationRunResult(BaseModel):
    recommendations_created: int
    status: str
    message: str


class RecommendationSearchRequest(BaseModel):
    entity_id: str | None = None
    recommendation_type: RecommendationType | None = None
    status: RecommendationStatus | None = None
    limit: int = 100


class RecommendationActionRequest(BaseModel):
    recommendation_id: str
    status: RecommendationStatus
    reason: str | None = None
