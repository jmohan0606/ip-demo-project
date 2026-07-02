# Part 15.7 — Recommendation & Learning Engine

## Added

- Opportunity model
- Recommendation model
- Feedback event model
- Opportunity engine
- Recommendation engine
- Compliance validation service
- Feedback learning engine
- SQLite learning store
- Recommendation runtime facade
- Recommendation runtime APIs
- Graph persistence for Opportunity, Recommendation, Feedback and Memory
- Knowledge evidence retrieval per recommendation
- UI page for recommendation runtime and feedback learning

## APIs

```text
GET  /recommendation-runtime/status
POST /recommendation-runtime/generate
POST /recommendation-runtime/feedback
```

## Feedback behavior

| Action | UI color | Learning effect |
|---|---|---|
| Accept | Green | Positive reinforcement |
| Complete | Green | Strong positive reinforcement |
| Modify | Blue | Advisor preference learning |
| Ignore | Amber | Weak negative signal |
| Reject | Red | Negative reinforcement |

## Runtime

```text
FeatureRuntime → OpportunityEngine → RecommendationEngine → ComplianceService
  → KnowledgeRuntime evidence
  → GraphRuntime persistence
  → LearningStore feedback
  → Memory update
```

## Next step

Part 15.8 — Memory & Context Platform.
