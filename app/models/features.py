from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel, Field


class FeatureEntityType(StrEnum):
    ADVISOR = "Advisor"
    HOUSEHOLD = "Household"
    ACCOUNT = "Account"
    TRANSACTION = "Transaction"
    CRM = "CRM"
    AGP = "AGP"
    MARKET = "Market"
    REGION = "Region"
    FIRM = "Firm"


class FeatureGroupName(StrEnum):
    ADVISOR_GROWTH = "advisor_growth_features"
    HOUSEHOLD_OPPORTUNITY = "household_opportunity_features"
    ACCOUNT_REVENUE = "account_revenue_features"
    CRM_ACTIVITY = "crm_activity_features"
    AGP_PROGRESS = "agp_progress_features"
    FEEDBACK_LEARNING = "feedback_learning_features"


class FeatureDefinition(BaseModel):
    feature_name: str
    feature_group: FeatureGroupName
    entity_type: FeatureEntityType
    description: str
    data_type: str = "float"
    version: str = "1.0"


class FeatureVector(BaseModel):
    entity_type: FeatureEntityType
    entity_id: str
    feature_group: FeatureGroupName
    feature_version: str = "1.0"
    features: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FeatureMaterializationRequest(BaseModel):
    feature_groups: list[FeatureGroupName] = Field(default_factory=list)
    force_refresh: bool = True


class FeatureMaterializationResult(BaseModel):
    feature_group: FeatureGroupName
    entity_type: FeatureEntityType
    records_materialized: int
    status: str
    message: str
