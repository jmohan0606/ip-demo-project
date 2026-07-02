# GSQL Query Audit

**Static status:** PASS

> Live compilation and execution require the external TigerGraph 4.2.2 environment and are not claimed in this package.

| ID | Query | Parameters | SELECTs | Traversals | Accumulators | Test case | Static | Live |
|---|---|---:|---:|---:|---:|---|---|---|
| GQ-001 | `get_org_hierarchy` | 3 | 21 | 15 | 0 | Yes | PASS | Pending |
| GQ-002 | `get_scope_descendants` | 3 | 22 | 13 | 0 | Yes | PASS | Pending |
| GQ-003 | `get_management_chain` | 2 | 5 | 3 | 0 | Yes | PASS | Pending |
| GQ-004 | `get_revenue_summary_by_scope` | 5 | 26 | 17 | 8 | Yes | PASS | Pending |
| GQ-005 | `get_revenue_trend_by_scope` | 5 | 19 | 13 | 3 | Yes | PASS | Pending |
| GQ-006 | `get_product_mix_by_scope` | 4 | 21 | 15 | 4 | Yes | PASS | Pending |
| GQ-007 | `get_top_bottom_advisors` | 6 | 20 | 12 | 2 | Yes | PASS | Pending |
| GQ-008 | `get_peer_benchmark` | 4 | 9 | 6 | 5 | Yes | PASS | Pending |
| GQ-009 | `get_advisor_360` | 1 | 16 | 15 | 0 | Yes | PASS | Pending |
| GQ-010 | `get_advisor_book_of_business` | 2 | 4 | 3 | 3 | Yes | PASS | Pending |
| GQ-011 | `get_household_360` | 1 | 13 | 12 | 0 | Yes | PASS | Pending |
| GQ-012 | `get_account_holdings_and_activity` | 1 | 11 | 10 | 0 | Yes | PASS | Pending |
| GQ-013 | `get_agp_enrollment_summary` | 1 | 7 | 6 | 0 | Yes | PASS | Pending |
| GQ-014 | `get_agp_milestone_timeline` | 1 | 5 | 4 | 0 | Yes | PASS | Pending |
| GQ-015 | `get_agp_kpi_measurements` | 2 | 6 | 5 | 0 | Yes | PASS | Pending |
| GQ-016 | `get_agp_coaching_history` | 1 | 6 | 5 | 0 | Yes | PASS | Pending |
| GQ-017 | `get_agp_crm_work_summary` | 1 | 4 | 3 | 7 | Yes | PASS | Pending |
| GQ-018 | `get_crm_leads` | 3 | 4 | 3 | 0 | Yes | PASS | Pending |
| GQ-019 | `get_crm_referrals` | 3 | 4 | 3 | 0 | Yes | PASS | Pending |
| GQ-020 | `get_crm_opportunities` | 3 | 5 | 4 | 0 | Yes | PASS | Pending |
| GQ-021 | `get_crm_pipeline_by_stage` | 1 | 2 | 1 | 4 | Yes | PASS | Pending |
| GQ-022 | `get_feature_snapshot` | 2 | 1 | 0 | 0 | Yes | PASS | Pending |
| GQ-023 | `get_feature_lineage` | 1 | 9 | 8 | 0 | Yes | PASS | Pending |
| GQ-024 | `get_embeddings_for_entity` | 2 | 1 | 0 | 0 | Yes | PASS | Pending |
| GQ-025 | `get_similar_entities` | 4 | 5 | 4 | 0 | Yes | PASS | Pending |
| GQ-026 | `get_predictions` | 2 | 3 | 2 | 0 | Yes | PASS | Pending |
| GQ-027 | `get_ai_opportunities` | 2 | 6 | 5 | 0 | Yes | PASS | Pending |
| GQ-028 | `get_recommendations` | 2 | 8 | 8 | 0 | Yes | PASS | Pending |
| GQ-029 | `get_recommendation_detail` | 1 | 9 | 8 | 0 | Yes | PASS | Pending |
| GQ-030 | `get_feedback_learning_history` | 1 | 5 | 4 | 0 | Yes | PASS | Pending |
| GQ-031 | `get_context_for_agent` | 3 | 27 | 23 | 2 | Yes | PASS | Pending |
| GQ-032 | `get_memory_timeline` | 2 | 3 | 2 | 0 | Yes | PASS | Pending |
| GQ-033 | `get_reasoning_trace` | 2 | 6 | 5 | 0 | Yes | PASS | Pending |
| GQ-034 | `get_graph_subgraph` | 4 | 16 | 12 | 0 | Yes | PASS | Pending |
| GQ-035 | `get_notifications_for_user` | 3 | 2 | 1 | 0 | Yes | PASS | Pending |
| GQ-036 | `get_data_health_summary` | 0 | 2 | 0 | 4 | Yes | PASS | Pending |
| GQ-037 | `get_agent_execution_trace` | 1 | 5 | 4 | 0 | Yes | PASS | Pending |
| GQ-038 | `get_what_if_baseline` | 3 | 5 | 3 | 0 | Yes | PASS | Pending |
| GQ-039 | `get_agp_program_cohort_summary` | 4 | 21 | 15 | 5 | Yes | PASS | Pending |
| GQ-040 | `get_insight_coaching_context` | 4 | 43 | 35 | 2 | Yes | PASS | Pending |
| GQ-041 | `get_recommendation_adoption_learning_summary` | 2 | 21 | 15 | 7 | Yes | PASS | Pending |
| GQ-042 | `get_persona_scope_assignments` | 1 | 10 | 9 | 0 | Yes | PASS | Pending |
| GQ-043 | `get_data_quality_issues` | 3 | 10 | 5 | 8 | Yes | PASS | Pending |

## Errors
- None
