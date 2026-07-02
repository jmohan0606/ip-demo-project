from __future__ import annotations

from app.models.features import FeatureDefinition, FeatureEntityType, FeatureGroupName


FEATURE_DEFINITIONS = [
    FeatureDefinition(feature_name="revenue_ltm", feature_group=FeatureGroupName.ADVISOR_GROWTH, entity_type=FeatureEntityType.ADVISOR, description="Advisor trailing revenue from demo transactions."),
    FeatureDefinition(feature_name="managed_revenue_ltm", feature_group=FeatureGroupName.ADVISOR_GROWTH, entity_type=FeatureEntityType.ADVISOR, description="Advisor managed revenue."),
    FeatureDefinition(feature_name="managed_revenue_pct", feature_group=FeatureGroupName.ADVISOR_GROWTH, entity_type=FeatureEntityType.ADVISOR, description="Managed revenue share of total revenue."),
    FeatureDefinition(feature_name="nnm_ltm", feature_group=FeatureGroupName.ADVISOR_GROWTH, entity_type=FeatureEntityType.ADVISOR, description="Advisor net new money."),
    FeatureDefinition(feature_name="ncf_ltm", feature_group=FeatureGroupName.ADVISOR_GROWTH, entity_type=FeatureEntityType.ADVISOR, description="Advisor net cash flow."),
    FeatureDefinition(feature_name="household_count", feature_group=FeatureGroupName.ADVISOR_GROWTH, entity_type=FeatureEntityType.ADVISOR, description="Number of served households."),
    FeatureDefinition(feature_name="crm_activity_count", feature_group=FeatureGroupName.CRM_ACTIVITY, entity_type=FeatureEntityType.ADVISOR, description="CRM activity volume."),
    FeatureDefinition(feature_name="meeting_count", feature_group=FeatureGroupName.CRM_ACTIVITY, entity_type=FeatureEntityType.ADVISOR, description="Meeting count."),
    FeatureDefinition(feature_name="followup_count", feature_group=FeatureGroupName.CRM_ACTIVITY, entity_type=FeatureEntityType.ADVISOR, description="Follow-up count."),
    FeatureDefinition(feature_name="goal_count", feature_group=FeatureGroupName.AGP_PROGRESS, entity_type=FeatureEntityType.ADVISOR, description="AGP goal count."),
    FeatureDefinition(feature_name="off_track_kpi_count", feature_group=FeatureGroupName.AGP_PROGRESS, entity_type=FeatureEntityType.ADVISOR, description="Off-track KPI count."),
    FeatureDefinition(feature_name="avg_goal_attainment_pct", feature_group=FeatureGroupName.AGP_PROGRESS, entity_type=FeatureEntityType.ADVISOR, description="Average goal attainment percentage."),
    FeatureDefinition(feature_name="household_aum", feature_group=FeatureGroupName.HOUSEHOLD_OPPORTUNITY, entity_type=FeatureEntityType.HOUSEHOLD, description="Household total AUM."),
    FeatureDefinition(feature_name="cash_balance", feature_group=FeatureGroupName.HOUSEHOLD_OPPORTUNITY, entity_type=FeatureEntityType.HOUSEHOLD, description="Household cash balance."),
    FeatureDefinition(feature_name="cash_to_aum_ratio", feature_group=FeatureGroupName.HOUSEHOLD_OPPORTUNITY, entity_type=FeatureEntityType.HOUSEHOLD, description="Cash balance divided by AUM."),
    FeatureDefinition(feature_name="account_value", feature_group=FeatureGroupName.ACCOUNT_REVENUE, entity_type=FeatureEntityType.ACCOUNT, description="Account value."),
    FeatureDefinition(feature_name="managed_flag", feature_group=FeatureGroupName.ACCOUNT_REVENUE, entity_type=FeatureEntityType.ACCOUNT, description="Managed account flag."),
]


def list_feature_definitions() -> list[FeatureDefinition]:
    return FEATURE_DEFINITIONS
