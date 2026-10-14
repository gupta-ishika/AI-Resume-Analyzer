import hashlib
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.errors import ConflictError, ValidationError
from backend.repositories.analysis_repo import AnalysisRepository
from backend.repositories.models import ResumeModel
from backend.repositories.requirements_repo import JobRequirementsRepository
from backend.repositories.resume_repo import ResumeRepository
from backend.schemas.common import AnalysisStatus, ResumeStatus
from backend.schemas.requirements import JobRequirements
from backend.services.analysis_service import AnalysisService
from backend.services.cleanup_service import CleanupService
from backend.services.embedding_service import default_vector_store
from backend.services.watchdog_service import WatchdogService
from backend.worker.tasks import process_resume_task


def create_temp_resume_file(content: str) -> tuple[str, str]:
    """Helper creating a temporary resume file in settings.TEMP_STORAGE_DIR."""
    storage_key = f"{uuid4()}.txt"
    file_path = Path(settings.TEMP_STORAGE_DIR) / storage_key
    file_path.write_text(content, encoding="utf-8")
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return storage_key, content_hash


def test_raw_file_lifecycle_and_guaranteed_deletion(db_session: Session):
    """
    BG-02 & BG-03: Raw file must be deleted after extraction attempt regardless of success/failure.
    """
    analysis = AnalysisRepository.create(db_session, name="Backend Developer Analysis")

    # Confirmed requirements
    job_req = JobRequirements(
        required_skills=["Python", "FastAPI"],
        confirmed_at=datetime.now(UTC),
    )
    JobRequirementsRepository.save_or_update(db_session, analysis.id, job_req)

    # 1. Valid resume
    resume_text = (
        "Jane Doe\n"
        "jane@example.com\n\n"
        "Technical Skills\n"
        "Python, FastAPI, Docker, SQL\n\n"
        "Professional Experience\n"
        "Senior Developer, 5 years\n"
        "Built REST APIs with FastAPI.\n\n"
        "Education\n"
        "B.S. in Computer Science\n"
    )
    storage_key, content_hash = create_temp_resume_file(resume_text)
    file_path = Path(settings.TEMP_STORAGE_DIR) / storage_key
    assert file_path.exists()

    resume = ResumeRepository.register_resume(
        db=db_session,
        analysis_id=analysis.id,
        original_filename="jane_doe_cv.txt",
        content_hash=content_hash,
        temp_storage_key=storage_key,
    )
    assert resume.status == ResumeStatus.READY.value

    # Process resume task synchronously
    result = process_resume_task(analysis.id, resume.id)
    assert result["status"] == "success"

    db_session.refresh(resume)
    assert resume.status == ResumeStatus.SUCCESS.value
    # Guaranteed raw file deletion in finally block
    assert not file_path.exists()


def test_resume_extraction_failure_deletes_raw_file(db_session: Session):
    """
    BG-02 & BG-03: If resume text extraction fails, status is marked FAILED,
    raw file is still deleted, and it does not halt other tasks.
    """
    analysis = AnalysisRepository.create(db_session, name="Data Engineer Analysis")
    job_req = JobRequirements(
        required_skills=["Python"],
        confirmed_at=datetime.now(UTC),
    )
    JobRequirementsRepository.save_or_update(db_session, analysis.id, job_req)

    # Empty file causes extraction failure
    storage_key, content_hash = create_temp_resume_file("")
    file_path = Path(settings.TEMP_STORAGE_DIR) / storage_key
    assert file_path.exists()

    resume = ResumeRepository.register_resume(
        db=db_session,
        analysis_id=analysis.id,
        original_filename="empty_file.txt",
        content_hash=content_hash,
        temp_storage_key=storage_key,
    )

    result = process_resume_task(analysis.id, resume.id)
    assert result["status"] == "failed"

    db_session.refresh(resume)
    assert resume.status == ResumeStatus.FAILED.value
    assert resume.failure_category is not None
    # Raw file must still be removed
    assert not file_path.exists()


def test_start_analysis_state_machine_and_concurrency(db_session: Session):
    """
    BG-04: Start Analysis transitions REQUIREMENTS_PENDING -> PROCESSING,
    enqueues tasks, and rejects duplicate start calls.
    """
    analysis = AnalysisRepository.create(db_session, name="Full Stack Analysis")

    # Cannot start with unconfirmed requirements
    with pytest.raises(ValidationError) as exc_info:
        AnalysisService.start_analysis(db_session, analysis.id)
    assert exc_info.value.code == "REQUIREMENTS_UNCONFIRMED"

    job_req = JobRequirements(
        required_skills=["React", "TypeScript"],
        confirmed_at=datetime.now(UTC),
    )
    JobRequirementsRepository.save_or_update(db_session, analysis.id, job_req)

    # Cannot start with zero READY resumes
    with pytest.raises(ValidationError) as exc_info:
        AnalysisService.start_analysis(db_session, analysis.id)
    assert exc_info.value.code == "NO_READY_RESUMES"

    # Add a READY resume
    storage_key, content_hash = create_temp_resume_file("Resume content here")
    ResumeRepository.register_resume(
        db=db_session,
        analysis_id=analysis.id,
        original_filename="resume.txt",
        content_hash=content_hash,
        temp_storage_key=storage_key,
    )

    # Start analysis successfully
    task_ids = AnalysisService.start_analysis(db_session, analysis.id)
    assert len(task_ids) == 1

    db_session.refresh(analysis)
    assert analysis.status in (
        AnalysisStatus.PROCESSING.value,
        AnalysisStatus.RANKED.value,
    )

    # A repeated start attempt raises conflict
    with pytest.raises(ConflictError) as exc_info:
        AnalysisService.start_analysis(db_session, analysis.id)
    assert exc_info.value.code == "ANALYSIS_ALREADY_STARTED"

    # Cleanup temp file
    CleanupService.delete_temporary_file(storage_key)


def test_expired_pending_resumes_cleanup(db_session: Session):
    """
    BG-02: Resumes in REQUIREMENTS_PENDING exceeding retention are deleted
    and marked REJECTED with UPLOAD_EXPIRED.
    """
    analysis = AnalysisRepository.create(db_session, name="Old Analysis")
    storage_key, content_hash = create_temp_resume_file("Old candidate text")
    file_path = Path(settings.TEMP_STORAGE_DIR) / storage_key

    resume = ResumeRepository.register_resume(
        db=db_session,
        analysis_id=analysis.id,
        original_filename="old_resume.txt",
        content_hash=content_hash,
        temp_storage_key=storage_key,
    )

    # Manually backdate created_at past 24 hours
    resume.created_at = datetime.now(UTC) - timedelta(hours=25)
    db_session.commit()

    cleaned = CleanupService.cleanup_expired_pending_resumes(db_session, max_age_hours=24)
    assert cleaned >= 1

    db_session.refresh(resume)
    assert resume.status == ResumeStatus.REJECTED.value
    assert resume.failure_reason_code == "UPLOAD_EXPIRED"
    assert not file_path.exists()


def test_orphaned_temporary_files_cleanup(db_session: Session):
    """
    BG-02: Files in temporary storage not tracked by any database resume are swept.
    """
    # Create an orphaned file
    storage_key = f"orphaned_{uuid4()}.txt"
    file_path = Path(settings.TEMP_STORAGE_DIR) / storage_key
    file_path.write_text("Orphaned data", encoding="utf-8")

    # Set min_age_seconds=0 for immediate test sweeping
    time.sleep(0.01)
    orphaned_count = CleanupService.cleanup_orphaned_temporary_files(
        db_session, min_age_seconds=0
    )
    assert orphaned_count >= 1
    assert not file_path.exists()


def test_finalization_all_resumes_failed_transitions_to_ranked(db_session: Session):
    """
    BG-05: If every resume fails, analysis still transitions to RANKED with empty ranking.
    """
    analysis = AnalysisRepository.create(db_session, name="All Failed Analysis")
    analysis.status = AnalysisStatus.PROCESSING.value
    db_session.commit()

    # Create failed resume
    r1 = ResumeModel(
        analysis_id=analysis.id,
        original_filename="corrupted.pdf",
        content_hash="hash_1",
        status=ResumeStatus.FAILED.value,
        failure_category="DOCUMENT_CORRUPTED",
    )
    db_session.add(r1)
    db_session.commit()

    finalized = WatchdogService.finalize_analysis(db_session, analysis.id)
    assert finalized is True

    db_session.refresh(analysis)
    assert analysis.status == AnalysisStatus.RANKED.value


def test_watchdog_cycle_reclaims_stale_processing_and_lost_finalization(db_session: Session):
    """
    BG-05: Watchdog cycle recovers lost finalizations and reclaims stale processing tasks.
    """
    analysis = AnalysisRepository.create(db_session, name="Watchdog Test Analysis")
    analysis.status = AnalysisStatus.PROCESSING.value
    db_session.commit()

    # 1. Stale processing resume: retry_count = 0 -> should reset to READY
    r1 = ResumeModel(
        analysis_id=analysis.id,
        original_filename="stale_1.txt",
        content_hash="hash_stale_1",
        status=ResumeStatus.PROCESSING.value,
        processing_started_at=datetime.now(UTC) - timedelta(seconds=700),
        retry_count=0,
    )
    # 2. Stale processing resume: retry_count = 3 -> should fail with timeout
    r2 = ResumeModel(
        analysis_id=analysis.id,
        original_filename="stale_2.txt",
        content_hash="hash_stale_2",
        status=ResumeStatus.PROCESSING.value,
        processing_started_at=datetime.now(UTC) - timedelta(seconds=700),
        retry_count=3,
    )
    db_session.add_all([r1, r2])
    db_session.commit()

    stats = WatchdogService.run_watchdog_cycle(db_session)

    db_session.refresh(r1)
    db_session.refresh(r2)

    assert stats["stale_processing_reset"] >= 1
    assert r2.status == ResumeStatus.FAILED.value
    assert r2.failure_reason_code == "PROCESSING_TIMEOUT"
    assert stats["stale_processing_failed"] >= 1


def test_analysis_deletion_rules_and_vector_cleanup(db_session: Session):
    """
    BG-06:
    - Deletion is rejected with ConflictError while PROCESSING.
    - Soft deletion hides analysis.
    - Vector collection and PostgreSQL records are permanently cleaned up.
    """
    analysis = AnalysisRepository.create(db_session, name="Deletion Test Analysis")
    analysis.status = AnalysisStatus.PROCESSING.value
    db_session.commit()

    # 1. Attempt delete while PROCESSING -> must raise ConflictError
    with pytest.raises(ConflictError) as exc_info:
        CleanupService.delete_analysis(db_session, analysis.id)
    assert exc_info.value.code == "ANALYSIS_PROCESSING"

    # 2. Transition to RANKED -> deletion must succeed
    analysis.status = AnalysisStatus.RANKED.value
    db_session.commit()

    # Index document in vector store
    default_vector_store.upsert_document(analysis.id, "cand_doc", "some text")
    assert f"analysis_{analysis.id}" in default_vector_store._collections

    # Create temporary file associated with a resume
    storage_key, content_hash = create_temp_resume_file("Delete me with analysis")
    ResumeRepository.register_resume(
        db=db_session,
        analysis_id=analysis.id,
        original_filename="resume_to_delete.txt",
        content_hash=content_hash,
        temp_storage_key=storage_key,
    )

    # Execute deletion
    success = CleanupService.delete_analysis(db_session, analysis.id)
    assert success is True

    # Vector collection deleted
    assert f"analysis_{analysis.id}" not in default_vector_store._collections

    # Temp file deleted
    file_path = Path(settings.TEMP_STORAGE_DIR) / storage_key
    assert not file_path.exists()

    # Database record permanently deleted
    deleted_model = AnalysisRepository.get_by_id(db_session, analysis.id)
    assert deleted_model is None
