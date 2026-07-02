# TigerGraph Schema & Query Coverage Audit — Part 15.1

| Capability | Current Coverage | Required Update |
|---|---|---|
| Advisor hierarchy Firm → Division → Region → Market → Advisor | Good foundation | Add persona rollup query contracts for MDW/DDW/Firm |
| Revenue / AUM / NNM / NCF analytics | Good foundation | Add page API mapping and filter-scoped query wrappers |
| Household / Account / Transaction drilldown | Good foundation | Add transaction lineage query for detail drawers |
| AGP Goals / Coaching / MDW-DDW reviews | Partial | Add AGPReview, CoachingAction, GoalMilestone edges if not already present |
| Opportunities | Good foundation | Add opportunity detail / status transition queries |
| Recommendations | Good foundation | Add accept/reject/ignore/modify feedback mutation queries |
| Feedback Learning | Partial | Add LearningSignal vertex and LEARNED_FROM / UPDATED_MEMORY edges |
| Memory Timeline | Partial | Add typed memory queries: Episodic, Semantic, Reasoning, Conversation, LongTerm |
| Agent Traces / Tool Calls | Needs new graph model | Add AgentExecution, ToolCall, TraceStep vertices/edges |
| Feature Store | Partial | Add FeatureVector vertex and HAS_FEATURE_VECTOR edge |
| Graph Embeddings | Partial | Add EmbeddingVector metadata vertex or external vector reference |
| Similarity Search | Partial | Add SIMILAR_TO weighted edges or query result model |
| What-If Scenarios | Needs new graph model | Add Scenario, ScenarioAssumption, ScenarioOutcome vertices |
| Document Ingestion / Chroma lineage | Needs new graph model | Add Document, DocumentChunk, IndexedInCollection vertices and USED_DOCUMENT edges |
| Compliance | Partial | Add ComplianceRule, ComplianceCheck, PASSED/REQUIRES_REVIEW relations |

## Summary

The previous TigerGraph model is strong for revenue, hierarchy, advisor, household, product and recommendation basics.

For the upgraded UI and end-to-end behavior, the main missing graph areas are document ingestion lineage, scenario persistence, agent trace/tool-call persistence, recommendation feedback lifecycle, feature/embedding metadata, and persona-specific rollup query wrappers.
