from datetime import datetime

from pydantic import BaseModel, Field

from backend.schemas.candidate import (
    CandidateContact,
    EducationItem,
    ExperienceItem,
    ProjectItem,
)
from backend.schemas.common import (
    AnalysisStatus,
    ExplanationState,
    ResumeStatus,
    ScoreComponent,
)
from backend.schemas.explanation import ValidatedExplanation
from backend.schemas.matching import (
    ExperienceEvidenceItem,
    ScoreBreakdown,
    SkillMatchEvidence,
)


# --- 6.2 Analyses and Requirements ---
class AnalysisSummary(BaseModel):
    id: str
    name: str
    status: AnalysisStatus
    candidate_count: int = 0
    failure_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class AnalysisListResponse(BaseModel):
    items: list[AnalysisSummary]
    page: int
    limit: int
    total: int


class RequirementsResponse(BaseModel):
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    experience_requirements: list[str] = Field(default_factory=list)
    education_requirements: list[str] = Field(default_factory=list)
    explicit_requirements: list[str] = Field(default_factory=list)
    confirmed_at: datetime | None = None


class CreateAnalysisResponse(BaseModel):
    analysis: AnalysisSummary
    requirements: RequirementsResponse
    needs_manual_input: bool = False


# --- 6.3 Resumes ---
class UploadResultItem(BaseModel):
    filename: str
    resume_id: str | None = None
    status: str  # READY | DUPLICATE | REJECTED
    reason_code: str | None = None
    duplicate_of: str | None = None


class UploadResumesResponse(BaseModel):
    results: list[UploadResultItem]
    accepted_count: int
    limit: int = 50


class ResumeItem(BaseModel):
    resume_id: str
    filename: str
    status: ResumeStatus
    reason_code: str | None = None
    created_at: datetime


class ResumeListResponse(BaseModel):
    items: list[ResumeItem]


# --- 6.4 Start and Status ---
class StartResponse(BaseModel):
    analysis_id: str
    status: str = "PROCESSING"


class StatusResponse(BaseModel):
    status: AnalysisStatus
    total: int
    processed: int
    successful: int
    needs_review: int
    failed: int
    remaining: int
    duplicates_excluded: int
    rejected_excluded: int
    failure_reason: str | None = None


# --- 6.5 Candidates ---
class RankedCandidateItem(BaseModel):
    rank: int
    candidate_id: str
    label: str
    match_score: float
    required_skill_coverage: ScoreComponent
    relevant_experience: ScoreComponent


class ExcludedFileItem(BaseModel):
    resume_id: str
    filename: str
    status: str  # FAILED | NEEDS_REVIEW
    reason_code: str | None = None
    message: str | None = None


class CandidateListResponse(BaseModel):
    analysis_id: str
    status: AnalysisStatus
    ranking: list[RankedCandidateItem]
    excluded_files: list[ExcludedFileItem] = Field(default_factory=list)


class CandidateIdentityBlock(BaseModel):
    name: str
    contact: CandidateContact


class CandidateExtractedBlock(BaseModel):
    skills: list[str] = Field(default_factory=list)
    experience: list[ExperienceItem] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)


class CandidateMatchingBlock(BaseModel):
    match_score: float
    breakdown: ScoreBreakdown
    required_skills: SkillMatchEvidence
    preferred_skills: SkillMatchEvidence
    experience_evidence: list[ExperienceEvidenceItem] = Field(default_factory=list)


class CandidateExplanationBlock(BaseModel):
    state: ExplanationState


class CandidateDetailResponse(BaseModel):
    candidate_id: str
    label: str
    rank: int | None = None
    identity: CandidateIdentityBlock
    extracted: CandidateExtractedBlock
    matching: CandidateMatchingBlock
    explanation: CandidateExplanationBlock


# --- 6.6 Explanation ---
class ExplanationResponse(BaseModel):
    state: ExplanationState
    explanation: ValidatedExplanation | None = None
    failure_reason: str | None = None
