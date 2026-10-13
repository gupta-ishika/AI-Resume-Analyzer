from datetime import datetime

from pydantic import BaseModel, Field

from backend.schemas.common import ExplanationState


class ExplanationData(BaseModel):
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    experience_alignment: str
    assessment: str
    generated_at: datetime | None = None


class ExplanationResponse(BaseModel):
    state: ExplanationState
    explanation: ExplanationData | None = None
    failure_reason: str | None = None
