from datetime import datetime

from pydantic import BaseModel, Field


class JobRequirements(BaseModel):
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    experience_requirements: list[str] = Field(default_factory=list)
    education_requirements: list[str] = Field(default_factory=list)
    explicit_requirements: list[str] = Field(default_factory=list)
    job_relevant_text: str = ""
    confirmed_at: datetime | None = None


class JobRequirementsUpdate(BaseModel):
    required_skills: list[str]
    preferred_skills: list[str]
    experience_requirements: list[str]
    education_requirements: list[str]
    explicit_requirements: list[str]
