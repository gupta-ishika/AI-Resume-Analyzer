from pydantic import BaseModel, Field

from backend.schemas.common import EducationMatch, ScoreComponent


class MatchingProfile(BaseModel):
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    experience_requirements: list[str] = Field(default_factory=list)
    education_requirements: list[str] = Field(default_factory=list)
    explicit_requirements: list[str] = Field(default_factory=list)
    job_relevant_text: str = ""


class ScoreBreakdown(BaseModel):
    semantic_relevance: ScoreComponent
    required_skill_coverage: ScoreComponent
    preferred_skill_coverage: ScoreComponent
    relevant_experience: ScoreComponent
    education: EducationMatch


class SkillMatchEvidence(BaseModel):
    matched: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)


class ExperienceEvidenceItem(BaseModel):
    summary: str


class MatchResultData(BaseModel):
    candidate_id: str
    match_score: float  # 0 to 100
    rank: int | None = None
    breakdown: ScoreBreakdown
    required_skills: SkillMatchEvidence
    preferred_skills: SkillMatchEvidence
    experience_evidence: list[ExperienceEvidenceItem] = Field(default_factory=list)
    config_version: str = "1.0.0"
