# Sequence Diagrams

## Recommendation Feedback Loop

```text
User
  -> Streamlit Feedback Learning
  -> FeedbackLearningService
  -> RecommendationRepository
  -> FeedbackRepository
  -> LearningSignalEngine
  -> MemoryService
  -> GraphAccessClient
  -> MCP / REST / Mock
```

## AI Assistant Chat

```text
User
  -> AI Assistant Chat UI
  -> AiAssistantChatService
  -> ChatContextAssembler
  -> ContextService
  -> KnowledgeManagementService
  -> InsightsCoachingService
  -> Prediction/Opportunity/Recommendation Services
  -> Model Adapter
  -> Conversation Memory
```

## Data Upload

```text
User
  -> Data Ingestion & Sync UI
  -> IngestionService
  -> ValidationEngine
  -> DeltaDetector
  -> CheckpointRepository
  -> TigerGraphUpsertClient
  -> GraphAccessClient
  -> MCP / REST / Mock
```
