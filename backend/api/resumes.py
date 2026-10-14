from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.errors import NotFoundError, ValidationError
from backend.repositories.analysis_repo import AnalysisRepository
from backend.repositories.resume_repo import ResumeRepository
from backend.schemas.api import (
    ResumeItem,
    ResumeListResponse,
    UploadResultItem,
    UploadResumesResponse,
)
from backend.schemas.common import ResumeStatus
from backend.services.upload_service import ResumeUploadService

router = APIRouter(prefix="/analyses/{analysis_id}/resumes", tags=["Resumes"])


@router.post("", response_model=UploadResumesResponse)
async def upload_resumes(
    analysis_id: str,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """
    Uploads one or more resumes (PDF or DOCX, max 10MB each) for an analysis.
    Allowed only in REQUIREMENTS_PENDING status.
    Enforces 50 accepted resume limit and automatic duplicate detection.
    """
    analysis = AnalysisRepository.get_by_id(db, analysis_id)
    if not analysis or analysis.deletion_requested_at is not None:
        raise NotFoundError("ANALYSIS_NOT_FOUND", "Analysis not found.")

    if not files:
        raise ValidationError("NO_FILES_UPLOADED", "At least one resume file must be uploaded.")

    upload_results: list[UploadResultItem] = []

    for f in files:
        content = await f.read()
        filename = f.filename or "unknown.pdf"
        resume = ResumeUploadService.process_file_upload(
            db=db,
            analysis_id=analysis_id,
            filename=filename,
            file_bytes=content,
        )
        upload_results.append(
            UploadResultItem(
                filename=filename,
                resume_id=resume.id,
                status=resume.status,
                reason_code=resume.failure_reason_code,
                duplicate_of=resume.canonical_resume_id,
            )
        )

    accepted_count = ResumeRepository.count_accepted(db, analysis_id)
    return UploadResumesResponse(
        results=upload_results,
        accepted_count=accepted_count,
        limit=ResumeRepository.MAX_ACCEPTED_RESUMES,
    )


@router.get("", response_model=ResumeListResponse)
def list_resumes(analysis_id: str, db: Session = Depends(get_db)):
    """Lists every uploaded resume for the analysis with status and reason code."""
    analysis = AnalysisRepository.get_by_id(db, analysis_id)
    if not analysis or analysis.deletion_requested_at is not None:
        raise NotFoundError("ANALYSIS_NOT_FOUND", "Analysis not found.")

    resumes = ResumeRepository.list_by_analysis(db, analysis_id)
    items = [
        ResumeItem(
            resume_id=r.id,
            filename=r.original_filename,
            status=ResumeStatus(r.status),
            reason_code=r.failure_reason_code,
            created_at=r.created_at,
        )
        for r in resumes
    ]
    return ResumeListResponse(items=items)
