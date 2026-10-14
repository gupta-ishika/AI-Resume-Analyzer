import os
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.errors import ConflictError, NotFoundError
from backend.core.logging import get_logger
from backend.repositories.analysis_repo import AnalysisRepository
from backend.repositories.models import AnalysisModel, ResumeModel
from backend.repositories.resume_repo import ResumeRepository
from backend.schemas.common import AnalysisStatus, ResumeStatus
from backend.services.embedding_service import default_vector_store

logger = get_logger("cleanup_service")


class CleanupService:
    """
    Manages raw file lifecycle, retention, orphaned file sweeps,
    and analysis deletion with vector store cleanup.
    Owned by Person 2 per ARCHITECTURE.md and TASKS.md BG-02 & BG-06.
    """

    @staticmethod
    def get_storage_path(storage_key: str) -> Path:
        """Returns the full Path for a generated storage key in temp storage."""
        return Path(settings.TEMP_STORAGE_DIR) / storage_key

    @classmethod
    def delete_temporary_file(cls, storage_key: str | None) -> bool:
        """
        Safely deletes a temporary file by storage key.
        Guaranteed not to raise an error if already deleted or key is None.
        """
        if not storage_key:
            return False
        try:
            path = cls.get_storage_path(storage_key)
            if path.exists():
                path.unlink()
                logger.info(f"Deleted temporary storage file: {storage_key}")
                return True
        except Exception as e:
            logger.warning(f"Failed to delete temporary file {storage_key}: {e}")
        return False

    @classmethod
    def cleanup_expired_pending_resumes(
        cls,
        db: Session,
        max_age_hours: int | None = None,
    ) -> int:
        """
        In REQUIREMENTS_PENDING analyses, deletes files that passed the retention
        window and marks resumes REJECTED with reason UPLOAD_EXPIRED.
        """
        hours = max_age_hours if max_age_hours is not None else settings.TEMP_FILE_RETENTION_HOURS
        expired_resumes = ResumeRepository.list_expired_pending(db, max_age_hours=hours)

        cleaned_count = 0
        for resume in expired_resumes:
            if resume.temp_storage_key:
                cls.delete_temporary_file(resume.temp_storage_key)

            ResumeRepository.update_status(
                db=db,
                resume_id=resume.id,
                to_status=ResumeStatus.REJECTED.value,
                failure_category="FILE_SYSTEM",
                failure_reason_code="UPLOAD_EXPIRED",
                failure_message=f"Upload expired after exceeding {hours} hours retention window.",
            )
            cleaned_count += 1

        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} expired pending resume uploads.")
        return cleaned_count

    @classmethod
    def cleanup_orphaned_temporary_files(
        cls,
        db: Session,
        min_age_seconds: int = 3600,
    ) -> int:
        """
        Deletes files in temp storage that are not registered in active resume records
        and exceed min_age_seconds.
        """
        temp_dir = Path(settings.TEMP_STORAGE_DIR)
        if not temp_dir.exists():
            return 0

        # Query all currently tracked storage keys in DB
        active_keys = set(
            db.scalars(
                select(ResumeModel.temp_storage_key).where(
                    ResumeModel.temp_storage_key.is_not(None)
                )
            ).all()
        )

        now = datetime.now(UTC).timestamp()
        orphaned_count = 0

        for file_path in temp_dir.iterdir():
            if not file_path.is_file():
                continue

            storage_key = file_path.name
            if storage_key in active_keys:
                continue

            try:
                mtime = os.path.getmtime(file_path)
                if (now - mtime) >= min_age_seconds:
                    file_path.unlink()
                    orphaned_count += 1
                    logger.info(f"Removed orphaned temp file: {storage_key}")
            except Exception as e:
                logger.warning(f"Error checking/removing temp file {file_path}: {e}")

        return orphaned_count

    @classmethod
    def delete_analysis(cls, db: Session, analysis_id: str) -> bool:
        """
        Executes BG-06 analysis deletion:
        - Rejected if analysis is currently PROCESSING.
        - Sets deletion marker (hides from queries).
        - Deletes ChromaDB vector collection.
        - Deletes remaining temporary files.
        - Permanently removes database rows.
        """
        analysis = db.scalar(select(AnalysisModel).where(AnalysisModel.id == analysis_id))
        if not analysis or analysis.deletion_requested_at is not None:
            raise NotFoundError("ANALYSIS_NOT_FOUND", "Analysis not found or already deleted.")

        if analysis.status == AnalysisStatus.PROCESSING.value:
            raise ConflictError(
                "ANALYSIS_PROCESSING",
                "Cannot delete an analysis while it is in PROCESSING status.",
            )

        # 1. Mark for deletion
        AnalysisRepository.mark_for_deletion(db, analysis_id)

        # 2. Delete vector collection (idempotent)
        try:
            default_vector_store.delete_collection(analysis_id)
        except Exception as e:
            logger.warning(
                f"Vector collection deletion failed for {analysis_id}, will be swept: {e}"
            )

        # 3. Delete any remaining raw files for resumes in this analysis
        resumes = ResumeRepository.list_by_analysis(db, analysis_id)
        for r in resumes:
            if r.temp_storage_key:
                cls.delete_temporary_file(r.temp_storage_key)

        # 4. Permanently remove PostgreSQL records
        AnalysisRepository.delete_permanently(db, analysis_id)
        logger.info(f"Analysis {analysis_id} and its associated assets deleted permanently.")
        return True

    @classmethod
    def sweep_pending_deletions(cls, db: Session) -> int:
        """
        Sweeps any analyses with a pending deletion marker where vector cleanup
        or DB cascade deletion may have been interrupted.
        """
        marked_analyses = list(
            db.scalars(
                select(AnalysisModel).where(AnalysisModel.deletion_requested_at.is_not(None))
            ).all()
        )

        swept_count = 0
        for analysis in marked_analyses:
            try:
                default_vector_store.delete_collection(analysis.id)
                resumes = ResumeRepository.list_by_analysis(db, analysis.id)
                for r in resumes:
                    if r.temp_storage_key:
                        cls.delete_temporary_file(r.temp_storage_key)
                AnalysisRepository.delete_permanently(db, analysis.id)
                swept_count += 1
            except Exception as e:
                logger.error(f"Error sweeping deletion for analysis {analysis.id}: {e}")

        return swept_count
