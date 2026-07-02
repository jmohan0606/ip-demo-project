# Business Scenario Validation

**Status:** PASS
- Passed: 48
- Failed: 0

## Passed Checks
- PERSONA_ROLES: roles=['ADMIN', 'ADVISOR', 'AGP_ADVISOR', 'AI_OPS', 'COMPLIANCE', 'DDW', 'EXEC', 'MDW', 'RDW']
- COUNT_phx_dm_firm.csv: expected=1, actual=1
- COUNT_phx_dm_division.csv: expected=3, actual=3
- COUNT_phx_dm_region.csv: expected=6, actual=6
- COUNT_phx_dm_market.csv: expected=12, actual=12
- COUNT_phx_dm_branch.csv: expected=24, actual=24
- COUNT_phx_dm_advisor.csv: expected=60, actual=60
- COUNT_phx_dm_household.csv: expected=360, actual=360
- COUNT_phx_dm_account.csv: expected=720, actual=720
- COUNT_phx_dm_product.csv: expected=64, actual=64
- COUNT_phx_dm_time_period.csv: expected=24, actual=24
- DIVISION_TO_FIRM: every division has one firm
- REGION_TO_DIVISION: every region has one division
- MARKET_TO_REGION: every market has one region
- BRANCH_TO_MARKET: every branch has one market
- ADVISOR_TO_BRANCH: every advisor has one branch
- ADVISOR_TO_MARKET: every advisor has one market
- RDW_TO_DDW: every RDW is managed by one DDW
- MDW_TO_RDW: every MDW is managed by one RDW
- ADVISOR_TO_MDW: every advisor is managed by one MDW
- HOUSEHOLD_TO_ADVISOR: every household has one advisor
- ACCOUNT_TO_HOUSEHOLD: every account has one household
- ACCOUNT_PRODUCT_COVERAGE: every account has product holdings
- AGP_MILESTONE_MONTHS: eight 3-month milestones through month 24
- AGP_ENROLLMENTS: 24 AGP enrollments
- AGP_PROGRESS_PER_ENROLLMENT: each enrollment has 8 milestone progress records
- AGP_KPI_PER_MILESTONE: each milestone progress has 5 KPI measurements
- AGP_STATUS_VARIETY: statuses=['AT_RISK', 'COMPLETED', 'ON_TRACK', 'UPCOMING']
- CRM_LEAD_VARIETY: statuses=['COMPLETED', 'CONVERTED', 'OVERDUE', 'PENDING']
- CRM_REFERRAL_VARIETY: statuses=['COMPLETED', 'CONVERTED', 'OVERDUE', 'PENDING']
- CRM_OPPORTUNITY_OUTCOMES: statuses=['LOST', 'OPEN', 'WON']
- CRM_PIPELINE_STAGES: stages=['CLOSED_LOST', 'CLOSED_WON', 'NEGOTIATE', 'PROPOSE', 'QUALIFY']
- SEVERITY_phx_dm_prediction_result.csv: severities=['ATTENTION', 'CRITICAL', 'INFO', 'URGENT']
- SEVERITY_phx_dm_opportunity.csv: severities=['ATTENTION', 'CRITICAL', 'INFO', 'URGENT']
- SEVERITY_phx_dm_recommendation.csv: severities=['ATTENTION', 'CRITICAL', 'INFO', 'URGENT']
- MEMORY_TAXONOMY: memory_types=['EPISODIC', 'OUTCOME', 'PREFERENCE', 'REASONING', 'SEMANTIC']
- FEEDBACK_ACTIONS: actions=['ACCEPT', 'COMPLETE', 'DEFER', 'NOT_RELEVANT', 'REJECT']
- PREDICTION_FEATURE_LINEAGE: every prediction links to a feature snapshot
- PREDICTION_REASONING_LINEAGE: every prediction links to reasoning
- OPPORTUNITY_FEATURE_LINEAGE: every opportunity links to a feature snapshot
- OPPORTUNITY_PREDICTION_LINEAGE: every opportunity links to a prediction
- OPPORTUNITY_REASONING_LINEAGE: every opportunity links to reasoning
- RECOMMENDATION_FEATURE_LINEAGE: every recommendation links to a feature snapshot
- RECOMMENDATION_OPPORTUNITY_LINEAGE: every recommendation links to an opportunity
- RECOMMENDATION_PREDICTION_LINEAGE: every recommendation links to a prediction
- RECOMMENDATION_REASONING_LINEAGE: every recommendation links to reasoning
- TIME_PERIOD_CONTINUITY: 24 unique monthly periods
- TRANSACTION_ADVISOR_COVERAGE: all advisors have transactions

## Errors
- None
