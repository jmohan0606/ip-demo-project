# GSQL Query Implementation Matrix

All query files are implemented and static-reviewed. Live compilation/execution remains pending until the target TigerGraph 4.2.2 gate is run.

| ID | Query | Parameters | Purpose | Static status | Live status |
|---|---|---|---|---|---|
| GQ-001 | `get_org_hierarchy` | `scope_type STRING, scope_id STRING, max_depth INT` | Return the organizational hierarchy rooted at a selected scope. | PASS | PENDING |
| GQ-002 | `get_scope_descendants` | `scope_type STRING, scope_id STRING, entity_type STRING` | Resolve authorized descendants for any hierarchy scope. | PASS | PENDING |
| GQ-003 | `get_management_chain` | `user_id STRING, advisor_id STRING` | Return DDW → RDW → MDW → Advisor management chain and requester context. | PASS | PENDING |
| GQ-004 | `get_revenue_summary_by_scope` | `scope_type STRING, scope_id STRING, period_type STRING, start_date DATETIME, end_date DATETIME` | Aggregate revenue, AUM, NCF, NNM and entity counts for a hierarchy scope. | PASS | PENDING |
| GQ-005 | `get_revenue_trend_by_scope` | `scope_type STRING, scope_id STRING, period_grain STRING, start_date DATETIME, end_date DATETIME` | Return revenue trend grouped by graph time period. | PASS | PENDING |
| GQ-006 | `get_product_mix_by_scope` | `scope_type STRING, scope_id STRING, start_date DATETIME, end_date DATETIME` | Return product-level revenue mix for a hierarchy scope. | PASS | PENDING |
| GQ-007 | `get_top_bottom_advisors` | `scope_type STRING, scope_id STRING, start_date DATETIME, end_date DATETIME, direction STRING, result_limit INT` | Rank advisors by revenue within an authorized scope. | PASS | PENDING |
| GQ-008 | `get_peer_benchmark` | `advisor_id STRING, peer_method STRING, start_date DATETIME, end_date DATETIME` | Compare an advisor with market peers and embedding-based similar advisors. | PASS | PENDING |
| GQ-009 | `get_advisor_360` | `advisor_id STRING` | Return a connected Advisor 360 view across business, CRM, AGP and AI artifacts. | PASS | PENDING |
| GQ-010 | `get_advisor_book_of_business` | `advisor_id STRING, result_limit INT` | Return households, accounts and household revenue summary for an advisor. | PASS | PENDING |
| GQ-011 | `get_household_360` | `household_id STRING` | Return complete household context and AI artifacts. | PASS | PENDING |
| GQ-012 | `get_account_holdings_and_activity` | `account_id STRING` | Return holdings, activities, transactions and AI artifacts for an account. | PASS | PENDING |
| GQ-013 | `get_agp_enrollment_summary` | `advisor_id STRING` | Return AGP enrollment, program, current progress and goal/KPI context. | PASS | PENDING |
| GQ-014 | `get_agp_milestone_timeline` | `enrollment_id STRING` | Return all eight AGP milestone progress records and KPI measurements. | PASS | PENDING |
| GQ-015 | `get_agp_kpi_measurements` | `enrollment_id STRING, milestone_id STRING` | Return KPI measurements for an AGP enrollment and optional milestone. | PASS | PENDING |
| GQ-016 | `get_agp_coaching_history` | `advisor_id STRING` | Return coaching sessions and manager reviews for an AGP advisor. | PASS | PENDING |
| GQ-017 | `get_agp_crm_work_summary` | `advisor_id STRING` | Aggregate AGP advisor lead, referral and CRM opportunity work. | PASS | PENDING |
| GQ-018 | `get_crm_leads` | `advisor_id STRING, status STRING, result_limit INT` | Return advisor CRM leads filtered by status and urgency. | PASS | PENDING |
| GQ-019 | `get_crm_referrals` | `advisor_id STRING, status STRING, result_limit INT` | Return advisor CRM referrals filtered by status. | PASS | PENDING |
| GQ-020 | `get_crm_opportunities` | `advisor_id STRING, status STRING, result_limit INT` | Return advisor CRM opportunities with related clients, accounts and products. | PASS | PENDING |
| GQ-021 | `get_crm_pipeline_by_stage` | `advisor_id STRING` | Aggregate CRM pipeline by sales stage. | PASS | PENDING |
| GQ-022 | `get_feature_snapshot` | `entity_type STRING, entity_id STRING` | Return all versioned feature snapshots for an entity. | PASS | PENDING |
| GQ-023 | `get_feature_lineage` | `feature_snapshot_id STRING` | Trace a feature snapshot to dependent predictions, opportunities, recommendations and reasoning. | PASS | PENDING |
| GQ-024 | `get_embeddings_for_entity` | `entity_type STRING, entity_id STRING` | Return embedding metadata for an entity. | PASS | PENDING |
| GQ-025 | `get_similar_entities` | `entity_type STRING, entity_id STRING, result_limit INT, min_score DOUBLE` | Return nearest-neighbor similarity records and target entities. | PASS | PENDING |
| GQ-026 | `get_predictions` | `target_type STRING, target_id STRING` | Return predictions with feature snapshots and reasoning evidence. | PASS | PENDING |
| GQ-027 | `get_ai_opportunities` | `target_type STRING, target_id STRING` | Return AI opportunities with prediction, CRM, feature and recommendation lineage. | PASS | PENDING |
| GQ-028 | `get_recommendations` | `target_type STRING, target_id STRING` | Return recommendations and their complete supporting lineage. | PASS | PENDING |
| GQ-029 | `get_recommendation_detail` | `recommendation_id STRING` | Return one recommendation with evidence, feedback and downstream learning. | PASS | PENDING |
| GQ-030 | `get_feedback_learning_history` | `recommendation_id STRING` | Return the recommendation feedback, outcome and learning lifecycle. | PASS | PENDING |
| GQ-031 | `get_context_for_agent` | `persona_user_id STRING, subject_id STRING, query_intent STRING` | Build a persona-aware agent context bundle for an advisor subject. | PASS | PENDING |
| GQ-032 | `get_memory_timeline` | `subject_type STRING, subject_id STRING` | Return active and historical memory for a subject. | PASS | PENDING |
| GQ-033 | `get_reasoning_trace` | `artifact_type STRING, artifact_id STRING` | Return reasoning trace and direct evidence objects for an AI artifact. | PASS | PENDING |
| GQ-034 | `get_graph_subgraph` | `root_type STRING, root_id STRING, max_depth INT, node_limit INT` | Return a bounded business subgraph for Graph Explorer. | PASS | PENDING |
| GQ-035 | `get_notifications_for_user` | `user_id STRING, status STRING, result_limit INT` | Return persona notifications ordered by severity and due date. | PASS | PENDING |
| GQ-036 | `get_data_health_summary` | `` | Return vertex cardinalities and connected-edge traversal counts by type. | PASS | PENDING |
| GQ-037 | `get_agent_execution_trace` | `execution_id STRING` | Return agent execution, tool calls, evaluations, guardrails and reasoning. | PASS | PENDING |
| GQ-038 | `get_what_if_baseline` | `scenario_type STRING, scope_type STRING, scope_id STRING` | Return stored what-if scenarios and current advisor baseline artifacts. | PASS | PENDING |
| GQ-039 | `get_agp_program_cohort_summary` | `program_id STRING, cohort STRING, scope_type STRING, scope_id STRING` | Aggregate AGP cohort enrollment and milestone status within an organizational scope. | PASS | PENDING |
| GQ-040 | `get_insight_coaching_context` | `persona_user_id STRING, scope_type STRING, scope_id STRING, subject_id STRING` | Return the combined business and AI context used for insight/coaching cards. | PASS | PENDING |
| GQ-041 | `get_recommendation_adoption_learning_summary` | `scope_type STRING, scope_id STRING` | Aggregate recommendation adoption, impact and feedback learning for a scope. | PASS | PENDING |
| GQ-042 | `get_persona_scope_assignments` | `user_id STRING` | Return all explicit persona scope assignments and management relationships. | PASS | PENDING |
| GQ-043 | `get_data_quality_issues` | `domain STRING, severity STRING, result_limit INT` | Detect missing mandatory graph relationships for core domains. | PASS | PENDING |
