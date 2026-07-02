from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel, Field


class FeedbackActor(StrEnum):
    ADVISOR = "Advisor"
    MDW = "MDW"
    DDW = "DDW"
    FIRM = "Firm"
    SYSTEM = "System"


class FeedbackAction(StrEnum):
    ACCEPT = "accept"
    REJECT = "reject"
    IGNORE = "ignore"
    COMPLETE = "complete"
    MODIFY = "modify"


class OutcomeType(StrEnum):
    REVENUE_IMPACT = "Revenue Impact"
    NNM_IMPACT = "NNM Impact"
    AUM_IMPACT = "AUM Impact"
    MEETING_SCHEDULED = "Meeting Scheduled"
    CLIENT_ENGAGED = "Client Engaged"
    PRODUCT_REVIEW_COMPLETED = "Product Review Completed"
    NO_IMPACT = "No Impact"


class LearningSignalType(StrEnum):
    RECOMMENDATION_REWARD = "Recommendation Reward"
    PLAYBOOK_EFFECTIVENESS = "Playbook Effectiveness"
    ADVISOR_PREFERENCE = "Advisor Preference"
    OPPORTUNITY_RANKING = "Opportunity Ranking"
    COMPLIANCE_REVIEW = "Compliance Review"


class FeedbackEventRecord(BaseModel):
    feedback_id: str
    recommendation_id: str
    actor: FeedbackActor
    action: FeedbackAction
    reason: str | None = None
    modified_action_text: str | None = None
    reward_score: float
    created_ts: datetime = Field(default_factory=datetime.utcnow)
    status: str = "Active"


class OutcomeEventRecord(BaseModel):
    outcome_id: str
    feedback_id: str
    recommendation_id: str
    outcome_type: OutcomeType
    outcome_value: float = 0.0
    outcome_summary: str
    created_ts: datetime = Field(default_factory=datetime.utcnow)
    status: str = "Active"


class LearningSignalRecord(BaseModel):
    learning_signal_id: str
    feedback_id: str
    recommendation_id: str
    outcome_id: str | None = None
    signal_type: LearningSignalType
    signal_value: float
    signal_summary: str
    ranking_weight_delta: float = 0.0
    memory_update_summary: str | None = None
    created_ts: datetime = Field(default_factory=datetime.utcnow)
    status: str = "Active"


class FeedbackSubmitRequest(BaseModel):
    recommendation_id: str
    actor: FeedbackActor = FeedbackActor.ADVISOR
    action: FeedbackAction
    reason: str | None = None
    modified_action_text: str | None = None
    outcome_type: OutcomeType | None = None
    outcome_value: float | None = None
    outcome_summary: str | None = None
    write_to_tigergraph: bool = True


class FeedbackSubmitResult(BaseModel):
    feedback: FeedbackEventRecord
    outcome: OutcomeEventRecord | None = None
    learning_signal: LearningSignalRecord
    recommendation_status_updated: bool
    memory_updated: bool


class FeedbackSearchRequest(BaseModel):
    recommendation_id: str | None = None
    actor: FeedbackActor | None = None
    action: FeedbackAction | None = None
    limit: int = 100
