from __future__ import annotations
from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel, Field

class MemoryType(StrEnum):
    FIRM = "Firm Memory"
    DIVISION = "Division Memory"
    REGION = "Region Memory"
    MARKET = "Market Memory"
    ADVISOR = "Advisor Memory"
    AGP = "AGP Memory"
    CRM = "CRM Memory"
    REVENUE = "Revenue Memory"
    RECOMMENDATION = "Recommendation Memory"
    FEEDBACK = "Feedback Memory"
    COACHING = "Coaching Memory"
    CONVERSATION = "Conversation Memory"
    REASONING = "Reasoning Memory"
    # Section 11.6 — the Temporal Knowledge Graph poster's 6 memory types per persona.
    # Conversation + Reasoning were already active; these four were schema-absent until now.
    SEMANTIC = "Semantic Memory"
    EPISODIC = "Episodic Memory"
    PROCEDURAL = "Procedural Memory"
    PREFERENCE = "Preference Memory"

class MemoryScopeType(StrEnum):
    FIRM = "Firm"
    DIVISION = "Division"
    REGION = "Region"
    MARKET = "Market"
    ADVISOR = "Advisor"
    HOUSEHOLD = "Household"
    ACCOUNT = "Account"

class ContextMemoryCreateRequest(BaseModel):
    memory_type: MemoryType
    scope_type: MemoryScopeType
    scope_id: str
    title: str
    summary: str
    facts: dict = Field(default_factory=dict)
    confidence: float = 0.80
    source: str = "local_demo"
    valid_from: datetime = Field(default_factory=datetime.utcnow)
    valid_to: datetime | None = None

class ContextMemory(BaseModel):
    memory_id: str
    memory_type: MemoryType
    scope_type: MemoryScopeType
    scope_id: str
    title: str
    summary: str
    facts: dict = Field(default_factory=dict)
    confidence: float = 0.80
    source: str = "local_demo"
    valid_from: datetime
    valid_to: datetime | None = None
    created_ts: datetime = Field(default_factory=datetime.utcnow)
    status: str = "Active"

class MemoryRetrievalRequest(BaseModel):
    scope_type: MemoryScopeType
    scope_id: str
    memory_types: list[MemoryType] = Field(default_factory=list)
    query: str | None = None
    limit: int = 10
    include_expired: bool = False

class ContextPackage(BaseModel):
    scope_type: MemoryScopeType
    scope_id: str
    query: str | None = None
    memories: list[ContextMemory] = Field(default_factory=list)
    context_summary: str
    evidence_count: int
    generated_at: datetime = Field(default_factory=datetime.utcnow)

class ConversationTurnCreateRequest(BaseModel):
    conversation_id: str
    user_question: str
    assistant_answer: str
    persona: str
    scope_type: MemoryScopeType
    scope_id: str

class ConversationTurn(BaseModel):
    conversation_turn_id: str
    conversation_id: str
    turn_ts: datetime = Field(default_factory=datetime.utcnow)
    user_question: str
    assistant_answer: str
    persona: str
    scope_type: MemoryScopeType
    scope_id: str
    status: str = "Active"

class ReasoningTraceCreateRequest(BaseModel):
    trace_type: str
    conclusion: str
    confidence: float
    reasoning_steps: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    recommendation_id: str | None = None
    prediction_id: str | None = None
    opportunity_id: str | None = None
    memory_ids: list[str] = Field(default_factory=list)

class ReasoningTrace(BaseModel):
    trace_id: str
    trace_type: str
    conclusion: str
    confidence: float
    reasoning_steps: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    created_ts: datetime = Field(default_factory=datetime.utcnow)
    status: str = "Active"
