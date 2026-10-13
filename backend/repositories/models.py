import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from backend.core.database import Base
from backend.schemas.common import (
    AnalysisStatus,
    ExplanationState,
    ResumeStatus,
)

# Use JSONB if Postgres, fallback to generic JSON for SQLite / unit tests
JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(UTC)


class AnalysisModel(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=AnalysisStatus.REQUIREMENTS_PENDING.value
    )
    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    deletion_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scoring_config_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0.0")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    # Relationships
    requirements: Mapped["JobRequirementsModel | None"] = relationship(
        "JobRequirementsModel",
        back_populates="analysis",
        uselist=False,
        cascade="all, delete-orphan",
    )
    resumes: Mapped[list["ResumeModel"]] = relationship(
        "ResumeModel", back_populates="analysis", cascade="all, delete-orphan"
    )
    candidates: Mapped[list["CandidateModel"]] = relationship(
        "CandidateModel", back_populates="analysis", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_analyses_updated_at", "updated_at"),
        Index("ix_analyses_deletion", "deletion_requested_at"),
    )


class JobRequirementsModel(Base):
    __tablename__ = "job_requirements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    analysis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analyses.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    required_skills: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False, default=list)
    preferred_skills: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False, default=list)
    experience_requirements: Mapped[list[str]] = mapped_column(
        JSON_TYPE, nullable=False, default=list
    )
    education_requirements: Mapped[list[str]] = mapped_column(
        JSON_TYPE, nullable=False, default=list
    )
    explicit_requirements: Mapped[list[str]] = mapped_column(
        JSON_TYPE, nullable=False, default=list
    )
    job_relevant_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    analysis: Mapped["AnalysisModel"] = relationship("AnalysisModel", back_populates="requirements")


class ResumeModel(Base):
    __tablename__ = "resumes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    analysis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=ResumeStatus.READY.value
    )

    failure_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    failure_reason_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    failure_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    canonical_resume_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True
    )
    temp_storage_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    analysis: Mapped["AnalysisModel"] = relationship("AnalysisModel", back_populates="resumes")
    candidate: Mapped["CandidateModel | None"] = relationship(
        "CandidateModel", back_populates="resume", uselist=False
    )

    __table_args__ = (
        Index("ix_resumes_analysis_status", "analysis_id", "status"),
        Index("ix_resumes_content_hash", "analysis_id", "content_hash"),
    )


class CandidateModel(Base):
    __tablename__ = "candidates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    analysis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False
    )
    resume_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resumes.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    display_label: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Candidate Identity (revealed only in candidate detail view)
    candidate_name: Mapped[str] = mapped_column(
        String(255), nullable=False, default="Unknown Candidate"
    )
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    contact_other: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False, default=list)

    # Extracted structured professional data
    extracted_skills: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False, default=list)
    extracted_experience: Mapped[list[dict]] = mapped_column(
        JSON_TYPE, nullable=False, default=list
    )
    extracted_projects: Mapped[list[dict]] = mapped_column(JSON_TYPE, nullable=False, default=list)
    extracted_education: Mapped[list[dict]] = mapped_column(JSON_TYPE, nullable=False, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    analysis: Mapped["AnalysisModel"] = relationship("AnalysisModel", back_populates="candidates")
    resume: Mapped["ResumeModel"] = relationship("ResumeModel", back_populates="candidate")
    match_result: Mapped["MatchResultModel | None"] = relationship(
        "MatchResultModel", back_populates="candidate", uselist=False, cascade="all, delete-orphan"
    )
    explanation: Mapped["ExplanationModel | None"] = relationship(
        "ExplanationModel", back_populates="candidate", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_candidates_analysis", "analysis_id"),
        UniqueConstraint("analysis_id", "display_label", name="uq_candidates_analysis_label"),
    )


class MatchResultModel(Base):
    __tablename__ = "match_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    candidate_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("candidates.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    analysis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False
    )

    match_score: Mapped[float] = mapped_column(Float, nullable=False)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)

    component_scores: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False, default=dict)
    matching_evidence: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False, default=dict)
    scoring_config_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0.0")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    candidate: Mapped["CandidateModel"] = relationship(
        "CandidateModel", back_populates="match_result"
    )

    __table_args__ = (
        Index("ix_match_results_analysis_rank", "analysis_id", "rank"),
        UniqueConstraint("analysis_id", "rank", name="uq_match_results_analysis_rank"),
    )


class ExplanationModel(Base):
    __tablename__ = "explanations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    candidate_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("candidates.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    analysis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False
    )

    state: Mapped[str] = mapped_column(
        String(50), nullable=False, default=ExplanationState.NOT_REQUESTED.value
    )
    explanation_content: Mapped[dict | None] = mapped_column(JSON_TYPE, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    generation_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    candidate: Mapped["CandidateModel"] = relationship(
        "CandidateModel", back_populates="explanation"
    )

    __table_args__ = (
        Index("ix_explanations_state", "state"),
    )
