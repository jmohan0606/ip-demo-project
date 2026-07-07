from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel, Field


class ChatPersona(StrEnum):
    ADVISOR = "Advisor"
    MDW = "MDW"
    DDW = "DDW"
    FIRM = "Firm"


class ChatScopeType(StrEnum):
    FIRM = "Firm"
    DIVISION = "Division"
    REGION = "Region"
    MARKET = "Market"
    ADVISOR = "Advisor"


class ChatContextSource(StrEnum):
    CONTEXT_MEMORY = "Context Memory"
    KNOWLEDGE_RAG = "Knowledge RAG"
    INSIGHTS = "Insights"
    RECOMMENDATIONS = "Recommendations"
    OPPORTUNITIES = "Opportunities"
    PREDICTIONS = "Predictions"
    COACHING_TASKS = "Coaching Tasks"
    RECOMMENDATION_LIFECYCLE = "Recommendation Actions & Impact"
    GRAPH_REASONING = "Graph Relational Reasoning"
    AGP_STATUS = "AGP Program Status"
    CRM_PIPELINE = "CRM Pipeline & Activities"
    HOUSEHOLD_RISK = "Household Risk (ML)"
    PEER_BENCHMARK = "GNN Peer Benchmark"
    LEARNING_STATE = "Feedback Learning State"


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    question: str
    persona: ChatPersona = ChatPersona.ADVISOR
    scope_type: ChatScopeType = ChatScopeType.ADVISOR
    scope_id: str = "ADV0001"
    include_memory: bool = True
    include_knowledge: bool = True
    include_insights: bool = True
    write_to_memory: bool = True
    write_to_tigergraph: bool = True


class ChatContextItem(BaseModel):
    source: ChatContextSource
    title: str
    content: str
    score: float | None = None
    metadata: dict = Field(default_factory=dict)


class ChatResponse(BaseModel):
    conversation_id: str
    conversation_turn_id: str
    answer: str
    persona: ChatPersona
    scope_type: ChatScopeType
    scope_id: str
    context_items: list[ChatContextItem] = Field(default_factory=list)
    reasoning_steps: list[str] = Field(default_factory=list)
    confidence: float = 0.80
    # Input/output guardrail outcomes (Security & Governance): what the guardrail layer detected
    # on the way in (PII redaction, prompt-injection/jailbreak) and out (PII filtering, toxicity,
    # grounding). Empty dict when guardrails found nothing.
    guardrails: dict = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ChatHistoryRecord(BaseModel):
    conversation_turn_id: str
    conversation_id: str
    question: str
    answer: str
    persona: ChatPersona
    scope_type: ChatScopeType
    scope_id: str
    created_ts: datetime
