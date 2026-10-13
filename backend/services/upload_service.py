import hashlib
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.errors import ConflictError, NotFoundError
from backend.repositories.analysis_repo import AnalysisRepository
from backend.repositories.models import ResumeModel
from backend.repositories.resume_repo import ResumeRepository
from backend.schemas.common import AnalysisStatus


class ResumeUploadService:
    """Service to handle resume upload validation, hashing, storage, and registration."""

    SUPPORTED_EXTENSIONS = {".pdf", ".docx"}
    MAX_FILE_BYTES = settings.MAX_RESUME_SIZE_MB * 1024 * 1024

    @classmethod
    def process_file_upload(
        cls,
        db: Session,
        analysis_id: str,
        filename: str,
        file_bytes: bytes,
    ) -> ResumeModel:
        analysis = AnalysisRepository.get_by_id(db, analysis_id)
        if not analysis:
            raise NotFoundError("ANALYSIS_NOT_FOUND", "Analysis not found.")

        if analysis.status != AnalysisStatus.REQUIREMENTS_PENDING.value:
            raise ConflictError(
                "ANALYSIS_ALREADY_STARTED",
                f"Cannot upload resumes when analysis is in '{analysis.status}' status.",
            )

        content_hash = hashlib.sha256(file_bytes).hexdigest()
        ext = Path(filename).suffix.lower()

        # 1. Validation: Unsupported format
        if ext not in cls.SUPPORTED_EXTENSIONS:
            return ResumeRepository.register_resume(
                db=db,
                analysis_id=analysis_id,
                original_filename=filename,
                content_hash=content_hash,
                is_rejected=True,
                rejection_reason_code="UNSUPPORTED_FILE_TYPE",
                rejection_message=f"File extension '{ext}' is not supported. Use PDF or DOCX.",
            )

        # 2. Validation: File size
        if len(file_bytes) > cls.MAX_FILE_BYTES:
            return ResumeRepository.register_resume(
                db=db,
                analysis_id=analysis_id,
                original_filename=filename,
                content_hash=content_hash,
                is_rejected=True,
                rejection_reason_code="FILE_TOO_LARGE",
                rejection_message=(
                    f"File exceeds maximum allowed size of {settings.MAX_RESUME_SIZE_MB}MB."
                ),
            )

        # 3. Save temporary file with generated UUID name (never original filename!)
        temp_key = f"{uuid.uuid4()}{ext}"
        temp_path = Path(settings.TEMP_STORAGE_DIR) / temp_key
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.write_bytes(file_bytes)

        # 4. Atomic registration with concurrency protection and duplicate detection
        resume = ResumeRepository.register_resume(
            db=db,
            analysis_id=analysis_id,
            original_filename=filename,
            content_hash=content_hash,
            temp_storage_key=temp_key,
        )

        # If detected as DUPLICATE or limit-exceeded REJECTED, delete the temp file immediately!
        if resume.status in ["DUPLICATE", "REJECTED"]:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass

        return resume
