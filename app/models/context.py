from __future__ import annotations
from pydantic import BaseModel, Field


class PersonaContext(BaseModel):
    user_id: str = "demo_user"
    user_name: str = "Demo User"
    persona: str = "Advisor"
    hierarchy_level: str = "Advisor"
    hierarchy_id: str = "ADV001"
    time_period: str = "YTD"


class PageLoadRequest(BaseModel):
    persona_context: PersonaContext
    page_name: str


class PageLoadStep(BaseModel):
    step_name: str
    status: str = "pending"
    detail: str | None = None
    progress_percent: int = 0


class PageLoadStatus(BaseModel):
    page_name: str
    overall_status: str
    progress_percent: int
    steps: list[PageLoadStep] = Field(default_factory=list)
