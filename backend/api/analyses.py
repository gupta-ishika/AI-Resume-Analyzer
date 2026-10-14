from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.errors import NotFoundError, ValidationError
from backend.repositories.analysis_repo import AnalysisRepository
from backend.repositories.candidate_repo import CandidateRepository
from backend.repositories.requirements_repo import JobRequirementsRepository
from backend.repositories.resume_repo import ResumeRepository
from backend.schemas.api import (
    AnalysisListResponse,
    AnalysisSummary,
    CreateAnalysisResponse,
    RequirementsResponse,
    StartResponse,
    StatusResponse,
)
from backend.schemas.common import AnalysisStatus, ResumeStatus
from backend.schemas.requirements import JobRequirementsUpdate
from backend.services.analysis_service import AnalysisService
from backend.services.cleanup_service import CleanupService
from backend.services.document_loader import DocumentLoaderService

router = APIRouter(prefix="/analyses", tags=["Analyses"])


@router.post("", response_model=CreateAnalysisResponse, status_code=status.HTTP_201_CREATED)
async def create_analysis(
    jd_file: UploadFile | None = File(None),
    jd_text: str | None = Form(None),
    name: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """
    Creates a new analysis from an uploaded JD document (PDF/DOCX) or pasted text.
    Extracts requirements and immediately deletes any uploaded file.
    """
    if (jd_file is None and not jd_text) or (jd_file is not None and jd_text):
        raise ValidationError(
            "INVALID_INPUT",
            "Provide exactly one of 'jd_file' or 'jd_text'.",
        )

    text_to_process = ""
    if jd_file:
        content = await jd_file.read()
        outcome = DocumentLoaderService.extract_text_from_bytes(content, jd_file.filename or "")
        if outcome.status.value != "SUCCESS" or not outcome.raw_text:
            raise ValidationError(
                "DOCUMENT_UNREADABLE",
                outcome.failure_message or "Failed to extract text from job description document.",
            )
        text_to_process = outcome.raw_text
    else:
        text_to_process = jd_text.strip() if jd_text else ""

    if not text_to_process:
        raise ValidationError("EMPTY_INPUT", "Job description text cannot be empty.")

    analysis, requirements = AnalysisService.create_analysis_from_jd(
        db=db,
        name=name,
        jd_text=text_to_process,
    )

    needs_manual = not requirements.required_skills and not requirements.experience_requirements

    return CreateAnalysisResponse(
        analysis=AnalysisSummary(
            id=analysis.id,
            name=analysis.name,
            status=AnalysisStatus(analysis.status),
            candidate_count=0,
            failure_reason=analysis.failure_reason,
            created_at=analysis.created_at,
            updated_at=analysis.updated_at,
        ),
        requirements=RequirementsResponse(
            required_skills=requirements.required_skills,
            preferred_skills=requirements.preferred_skills,
            experience_requirements=requirements.experience_requirements,
            education_requirements=requirements.education_requirements,
            explicit_requirements=requirements.explicit_requirements,
            confirmed_at=requirements.confirmed_at,
        ),
        needs_manual_input=needs_manual,
    )


@router.get("", response_model=AnalysisListResponse)
def list_analyses(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Lists saved analyses excluding those marked for deletion."""
    analyses, total = AnalysisRepository.list_active(db=db, page=page, limit=limit)

    items: list[AnalysisSummary] = []
    for a in analyses:
        candidates = CandidateRepository.list_by_analysis(db, a.id)
        items.append(
            AnalysisSummary(
                id=a.id,
                name=a.name,
                status=AnalysisStatus(a.status),
                candidate_count=len(candidates),
                failure_reason=a.failure_reason,
                created_at=a.created_at,
                updated_at=a.updated_at,
            )
        )

    return AnalysisListResponse(items=items, page=page, limit=limit, total=total)


@router.get("/{analysis_id}", response_model=AnalysisSummary)
def get_analysis(analysis_id: str, db: Session = Depends(get_db)):
    """Retrieves an analysis by ID."""
    analysis = AnalysisRepository.get_by_id(db, analysis_id)
    if not analysis or analysis.deletion_requested_at is not None:
        raise NotFoundError("ANALYSIS_NOT_FOUND", "Analysis not found.")

    candidates = CandidateRepository.list_by_analysis(db, analysis.id)
    return AnalysisSummary(
        id=analysis.id,
        name=analysis.name,
        status=AnalysisStatus(analysis.status),
        candidate_count=len(candidates),
        failure_reason=analysis.failure_reason,
        created_at=analysis.created_at,
        updated_at=analysis.updated_at,
    )


@router.delete("/{analysis_id}", status_code=status.HTTP_202_ACCEPTED)
def delete_analysis(analysis_id: str, db: Session = Depends(get_db)):
    """
    Atomically marks an analysis for deletion and cleans up vector data and records.
    Returns 202 Accepted.
    """
    CleanupService.delete_analysis(db, analysis_id)
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"message": "Analysis deletion initiated successfully."},
    )


@router.get("/{analysis_id}/requirements", response_model=RequirementsResponse)
def get_requirements(analysis_id: str, db: Session = Depends(get_db)):
    """Retrieves job requirements for an analysis."""
    analysis = AnalysisRepository.get_by_id(db, analysis_id)
    if not analysis or analysis.deletion_requested_at is not None:
        raise NotFoundError("ANALYSIS_NOT_FOUND", "Analysis not found.")

    reqs = JobRequirementsRepository.get_by_analysis_id(db, analysis_id)
    if not reqs:
        raise NotFoundError("REQUIREMENTS_NOT_FOUND", "Job requirements not found.")

    return RequirementsResponse(
        required_skills=reqs.required_skills,
        preferred_skills=reqs.preferred_skills,
        experience_requirements=reqs.experience_requirements,
        education_requirements=reqs.education_requirements,
        explicit_requirements=reqs.explicit_requirements,
        confirmed_at=reqs.confirmed_at,
    )


@router.put("/{analysis_id}/requirements", response_model=RequirementsResponse)
def update_requirements(
    analysis_id: str,
    updates: JobRequirementsUpdate,
    db: Session = Depends(get_db),
):
    """Updates job requirements while in REQUIREMENTS_PENDING status."""
    reqs = AnalysisService.update_requirements(db, analysis_id, updates)
    return RequirementsResponse(
        required_skills=reqs.required_skills,
        preferred_skills=reqs.preferred_skills,
        experience_requirements=reqs.experience_requirements,
        education_requirements=reqs.education_requirements,
        explicit_requirements=reqs.explicit_requirements,
        confirmed_at=reqs.confirmed_at,
    )


@router.post("/{analysis_id}/requirements/confirm", response_model=RequirementsResponse)
def confirm_requirements(analysis_id: str, db: Session = Depends(get_db)):
    """Confirms reviewed job requirements prior to starting analysis."""
    reqs = AnalysisService.confirm_requirements(db, analysis_id)
    return RequirementsResponse(
        required_skills=reqs.required_skills,
        preferred_skills=reqs.preferred_skills,
        experience_requirements=reqs.experience_requirements,
        education_requirements=reqs.education_requirements,
        explicit_requirements=reqs.explicit_requirements,
        confirmed_at=reqs.confirmed_at,
    )


@router.post("/{analysis_id}/start", response_model=StartResponse)
def start_analysis(analysis_id: str, db: Session = Depends(get_db)):
    """Starts asynchronous resume processing and ranking."""
    AnalysisService.start_analysis(db, analysis_id)
    return StartResponse(analysis_id=analysis_id, status="PROCESSING")


@router.get("/{analysis_id}/status", response_model=StatusResponse)
def get_analysis_status(analysis_id: str, db: Session = Depends(get_db)):
    """Returns processing progress and count breakdown for polling."""
    analysis = AnalysisRepository.get_by_id(db, analysis_id)
    if not analysis or analysis.deletion_requested_at is not None:
        raise NotFoundError("ANALYSIS_NOT_FOUND", "Analysis not found.")

    resumes = ResumeRepository.list_by_analysis(db, analysis_id)

    accepted = [
        r for r in resumes
        if r.status not in (ResumeStatus.DUPLICATE.value, ResumeStatus.REJECTED.value)
    ]
    total = len(accepted)
    terminal_statuses = (
        ResumeStatus.SUCCESS.value,
        ResumeStatus.FAILED.value,
        ResumeStatus.NEEDS_REVIEW.value,
    )
    processed = len([r for r in accepted if r.status in terminal_statuses])
    successful = len([r for r in accepted if r.status == ResumeStatus.SUCCESS.value])
    needs_review = len([r for r in accepted if r.status == ResumeStatus.NEEDS_REVIEW.value])
    failed = len([r for r in accepted if r.status == ResumeStatus.FAILED.value])
    remaining = max(0, total - processed)

    duplicates_excluded = len([r for r in resumes if r.status == ResumeStatus.DUPLICATE.value])
    rejected_excluded = len([r for r in resumes if r.status == ResumeStatus.REJECTED.value])

    return StatusResponse(
        status=AnalysisStatus(analysis.status),
        total=total,
        processed=processed,
        successful=successful,
        needs_review=needs_review,
        failed=failed,
        remaining=remaining,
        duplicates_excluded=duplicates_excluded,
        rejected_excluded=rejected_excluded,
        failure_reason=analysis.failure_reason,
    )
