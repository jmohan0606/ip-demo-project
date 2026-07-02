# Part 16.3 — Real Azure OpenAI / LLM Agent Activation

## Added

- Azure OpenAI adapter
- Mock LLM fallback
- LLM runtime facade
- Enterprise prompt templates
- AI assistant runtime
- Memory/context-grounded assistant response
- Recommendation narrative generation
- Conversation memory writeback
- LLM activation APIs
- LLM activation UI page

## Runtime order

```text
AI Assistant request
  → MemoryRuntime builds context packet
  → LlmRuntime
  → Azure OpenAI if configured
  → Mock LLM fallback if not configured
  → Memory writeback
  → UI answer + trace
```

## APIs

```text
GET  /llm-activation/status
POST /llm-activation/ask
POST /llm-activation/recommendation-narrative
```

## Required Azure env

```text
AZURE_OPENAI_ENABLED=true
AZURE_OPENAI_ENDPOINT=<endpoint>
AZURE_OPENAI_API_KEY=<key>
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT=<deployment>
```

## Local mode

With `AZURE_OPENAI_ENABLED=false`, the system remains runnable using deterministic mock LLM fallback.

## Next step

Part 16.4 — Final Runtime Build Fixes + Real Browser Screenshot Validation.
