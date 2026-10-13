from enum import StrEnum

from pydantic import BaseModel


class AnalysisStatus(StrEnum):
    REQUIREMENTS_PENDING = "REQUIREMENTS_PENDING"
    PROCESSING = "PROCESSING"
    RANKED = "RANKED"
    FAILED = "FAILED"


class ResumeStatus(StrEnum):
    READY = "READY"
    DUPLICATE = "DUPLICATE"
    REJECTED = "REJECTED"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class ExplanationState(StrEnum):
    NOT_REQUESTED = "NOT_REQUESTED"
    GENERATING = "GENERATING"
    READY = "READY"
    FAILED = "FAILED"


class ScoreComponentStatus(StrEnum):
    SCORED = "scored"
    NOT_SPECIFIED = "not_specified"
    INDETERMINATE = "indeterminate"


class ScoreComponent(BaseModel):
    status: ScoreComponentStatus
    value: float | None = None  # 0 to 100 when scored


class EducationMatchStatus(StrEnum):
    MET = "met"
    NOT_MET = "not_met"
    NOT_SPECIFIED = "not_specified"
    INDETERMINATE = "indeterminate"


class EducationMatch(BaseModel):
    status: EducationMatchStatus
    notes: str | None = None
