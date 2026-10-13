from datetime import UTC, datetime

from sqlalchemy.orm import Session

from backend.core.errors import ConflictError, NotFoundError, ValidationError
from backend.repositories.analysis_repo import AnalysisRepository
from backend.repositories.models import AnalysisModel, JobRequirementsModel
from backend.repositories.requirements_repo import JobRequirementsRepository
from backend.repositories.resume_repo import ResumeRepository
from backend.schemas.common import AnalysisStatus, ResumeStatus
from backend.schemas.requirements import JobRequirements, JobRequirementsUpdate
from backend.services.jd_extractor import JDExtractor


class AnalysisService:
    """Application service for Analysis lifecycle and Requirement management."""

    @classmethod
    def create_analysis_from_jd(
        cls,
        db: Session,
        name: str | None,
        jd_text: str,
    ) -> tuple[AnalysisModel, JobRequirements]:
        extracted_reqs = JDExtractor.extract_requirements(jd_text)
        analysis_name = name or (
            extracted_reqs.required_skills[0] + " Analysis"
            if extracted_reqs.required_skills
            else "New Resume Analysis"
        )

        analysis = AnalysisRepository.create(db, name=analysis_name)
        JobRequirementsRepository.save_or_update(db, analysis.id, extracted_reqs)
        return analysis, extracted_reqs

    @classmethod
    def update_requirements(
        cls,
        db: Session,
        analysis_id: str,
        updates: JobRequirementsUpdate,
    ) -> JobRequirementsModel:
        analysis = AnalysisRepository.get_by_id(db, analysis_id)
        if not analysis:
            raise NotFoundError("ANALYSIS_NOT_FOUND", "Analysis not found.")

        if analysis.status != AnalysisStatus.REQUIREMENTS_PENDING.value:
            raise ConflictError(
                "ANALYSIS_ALREADY_STARTED",
                f"Cannot edit requirements when analysis is in '{analysis.status}' status.",
            )

        existing = JobRequirementsRepository.get_by_analysis_id(db, analysis_id)
        job_relevant_text = existing.job_relevant_text if existing else ""

        updated_reqs = JobRequirements(
            required_skills=updates.required_skills,
            preferred_skills=updates.preferred_skills,
            experience_requirements=updates.experience_requirements,
            education_requirements=updates.education_requirements,
            explicit_requirements=updates.explicit_requirements,
            job_relevant_text=job_relevant_text,
            confirmed_at=None,  # Reset confirmation if requirements changed
        )

        return JobRequirementsRepository.save_or_update(db, analysis_id, updated_reqs)

    @classmethod
    def confirm_requirements(
        cls,
        db: Session,
        analysis_id: str,
    ) -> JobRequirementsModel:
        analysis = AnalysisRepository.get_by_id(db, analysis_id)
        if not analysis:
            raise NotFoundError("ANALYSIS_NOT_FOUND", "Analysis not found.")

        if analysis.status != AnalysisStatus.REQUIREMENTS_PENDING.value:
            raise ConflictError(
                "ANALYSIS_ALREADY_STARTED",
                "Requirements can only be confirmed while REQUIREMENTS_PENDING.",
            )

        reqs = JobRequirementsRepository.get_by_analysis_id(db, analysis_id)
        if not reqs or (not reqs.required_skills and not reqs.experience_requirements):
            raise ValidationError(
                "REQUIREMENTS_INSUFFICIENT",
                (
                    "Cannot confirm requirements: At least one required skill "
                    "or experience criterion is needed."
                ),
            )

        reqs.confirmed_at = datetime.now(UTC)
        db.commit()
        db.refresh(reqs)
        return reqs

    @classmethod
    def validate_ready_for_start(cls, db: Session, analysis_id: str) -> None:
        analysis = AnalysisRepository.get_by_id(db, analysis_id)
        if not analysis:
            raise NotFoundError("ANALYSIS_NOT_FOUND", "Analysis not found.")

        if analysis.status != AnalysisStatus.REQUIREMENTS_PENDING.value:
            raise ConflictError(
                "ANALYSIS_ALREADY_STARTED",
                f"Analysis has already started and is in '{analysis.status}' status.",
            )

        reqs = JobRequirementsRepository.get_by_analysis_id(db, analysis_id)
        if not reqs or not reqs.confirmed_at:
            raise ValidationError(
                "REQUIREMENTS_UNCONFIRMED",
                "Job requirements must be reviewed and confirmed before starting analysis.",
            )

        # Check that there is at least one READY resume
        resumes = ResumeRepository.list_by_analysis(db, analysis_id)
        ready_resumes = [r for r in resumes if r.status == ResumeStatus.READY.value]
        if not ready_resumes:
            raise ValidationError(
                "NO_READY_RESUMES",
                "At least one accepted resume in READY status is required to start analysis.",
            )
