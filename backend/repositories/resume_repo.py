from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from backend.repositories.models import AnalysisModel, ResumeModel
from backend.schemas.common import ResumeStatus


class ResumeRepository:
    """Repository for Resume persistence, duplicate detection, and upload-limit protection."""

    MAX_ACCEPTED_RESUMES = 50

    @classmethod
    def register_resume(
        cls,
        db: Session,
        analysis_id: str,
        original_filename: str,
        content_hash: str,
        temp_storage_key: str | None = None,
        is_rejected: bool = False,
        rejection_reason_code: str | None = None,
        rejection_message: str | None = None,
    ) -> ResumeModel:
        """
        Atomically registers an uploaded resume.
        Locks the analysis row to prevent race conditions exceeding the 50-resume limit.
        """
        # Lock analysis row for concurrency protection
        db.execute(
            select(AnalysisModel).where(AnalysisModel.id == analysis_id).with_for_update()
        )

        # 1. If already rejected at validation (e.g. format/size), record and return immediately
        if is_rejected:
            resume = ResumeModel(
                analysis_id=analysis_id,
                original_filename=original_filename,
                content_hash=content_hash,
                status=ResumeStatus.REJECTED.value,
                failure_reason_code=rejection_reason_code,
                failure_message=rejection_message,
                temp_storage_key=None,
            )
            db.add(resume)
            db.commit()
            db.refresh(resume)
            return resume

        # 2. Check for duplicate content within this analysis
        existing_canonical = db.scalar(
            select(ResumeModel).where(
                ResumeModel.analysis_id == analysis_id,
                ResumeModel.content_hash == content_hash,
                ResumeModel.status.in_([
                    ResumeStatus.READY.value,
                    ResumeStatus.PROCESSING.value,
                    ResumeStatus.SUCCESS.value,
                    ResumeStatus.FAILED.value,
                    ResumeStatus.NEEDS_REVIEW.value,
                ]),
            )
        )

        if existing_canonical:
            # Register as duplicate referencing the canonical resume
            resume = ResumeModel(
                analysis_id=analysis_id,
                original_filename=original_filename,
                content_hash=content_hash,
                status=ResumeStatus.DUPLICATE.value,
                canonical_resume_id=existing_canonical.id,
                temp_storage_key=None,
            )
            db.add(resume)
            db.commit()
            db.refresh(resume)
            return resume

        # 3. Check 50 accepted resumes limit (excluding DUPLICATE and REJECTED)
        accepted_count = db.scalar(
            select(func.count(ResumeModel.id)).where(
                ResumeModel.analysis_id == analysis_id,
                ResumeModel.status.notin_([
                    ResumeStatus.DUPLICATE.value,
                    ResumeStatus.REJECTED.value,
                ]),
            )
        ) or 0

        if accepted_count >= cls.MAX_ACCEPTED_RESUMES:
            # Reject due to limit reached
            resume = ResumeModel(
                analysis_id=analysis_id,
                original_filename=original_filename,
                content_hash=content_hash,
                status=ResumeStatus.REJECTED.value,
                failure_reason_code="RESUME_LIMIT_EXCEEDED",
                failure_message=(
                    f"Analysis has reached the limit of {cls.MAX_ACCEPTED_RESUMES} "
                    "accepted resumes."
                ),
                temp_storage_key=None,
            )
            db.add(resume)
            db.commit()
            db.refresh(resume)
            return resume

        # 4. Accepted valid resume: status READY
        resume = ResumeModel(
            analysis_id=analysis_id,
            original_filename=original_filename,
            content_hash=content_hash,
            status=ResumeStatus.READY.value,
            temp_storage_key=temp_storage_key,
        )
        db.add(resume)
        db.commit()
        db.refresh(resume)
        return resume

    @staticmethod
    def get_by_id(db: Session, resume_id: str) -> ResumeModel | None:
        return db.scalar(select(ResumeModel).where(ResumeModel.id == resume_id))

    @staticmethod
    def list_by_analysis(db: Session, analysis_id: str) -> list[ResumeModel]:
        return list(
            db.scalars(
                select(ResumeModel)
                .where(ResumeModel.analysis_id == analysis_id)
                .order_by(ResumeModel.created_at.asc())
            ).all()
        )

    @staticmethod
    def count_accepted(db: Session, analysis_id: str) -> int:
        return (
            db.scalar(
                select(func.count(ResumeModel.id)).where(
                    ResumeModel.analysis_id == analysis_id,
                    ResumeModel.status.notin_([
                        ResumeStatus.DUPLICATE.value,
                        ResumeStatus.REJECTED.value,
                    ]),
                )
            )
            or 0
        )

    @staticmethod
    def claim_resume(db: Session, resume_id: str) -> bool:
        """
        Atomically claims a resume from READY to PROCESSING, recording start timestamp.
        Returns True if claim succeeded, False if already claimed or in another status.
        """
        stmt = (
            update(ResumeModel)
            .where(
                ResumeModel.id == resume_id,
                ResumeModel.status == ResumeStatus.READY.value,
            )
            .values(
                status=ResumeStatus.PROCESSING.value,
                processing_started_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        result = db.execute(stmt)
        db.commit()
        return result.rowcount > 0

    @staticmethod
    def update_status(
        db: Session,
        resume_id: str,
        to_status: str,
        failure_category: str | None = None,
        failure_reason_code: str | None = None,
        failure_message: str | None = None,
    ) -> bool:
        stmt = (
            update(ResumeModel)
            .where(ResumeModel.id == resume_id)
            .values(
                status=to_status,
                failure_category=failure_category,
                failure_reason_code=failure_reason_code,
                failure_message=failure_message,
                temp_storage_key=None,  # Key is cleared when processed
                updated_at=datetime.now(UTC),
            )
        )
        result = db.execute(stmt)
        db.commit()
        return result.rowcount > 0
