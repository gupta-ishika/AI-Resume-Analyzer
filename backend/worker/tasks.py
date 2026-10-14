from backend.core.database import SessionLocal
from backend.core.logging import get_logger
from backend.repositories.candidate_repo import CandidateRepository
from backend.repositories.matching_repo import MatchResultRepository
from backend.repositories.requirements_repo import JobRequirementsRepository
from backend.repositories.resume_repo import ResumeRepository
from backend.schemas.common import ResumeStatus
from backend.schemas.requirements import JobRequirements
from backend.services.cleanup_service import CleanupService
from backend.services.document_loader import DocumentLoader
from backend.services.embedding_service import default_vector_store
from backend.services.matching_profile_builder import MatchingProfileBuilder
from backend.services.profile_builder import ProfileBuilder
from backend.services.profile_extractor import ProfileExtractor
from backend.services.scoring_engine import ScoringEngine
from backend.services.watchdog_service import WatchdogService
from backend.worker.celery_app import celery_app

logger = get_logger("worker_tasks")


@celery_app.task(
    name="backend.worker.tasks.process_resume_task",
    queue="resume_queue",
    max_retries=2,
    default_retry_delay=10,
)
def process_resume_task(analysis_id: str, resume_id: str) -> dict[str, str]:
    """
    Asynchronous Celery task processing a single resume:
    1. Atomically claims the resume (READY -> PROCESSING).
    2. Extracts text using DocumentLoader.
    3. Handles failure and unreadable outcomes explicitly.
    4. Extracts candidate profile and builds sanitized ScoringProfile.
    5. Computes multi-component match scores and evidence.
    6. Guarantees raw-file deletion in finally block.
    7. Triggers finalization if all resumes have completed.
    """
    db = SessionLocal()
    temp_key_to_delete: str | None = None

    try:
        # 1. Atomically claim resume
        claimed = ResumeRepository.claim_resume(db, resume_id)
        if not claimed:
            logger.info(f"Resume {resume_id} could not be claimed; skipping.")
            return {"status": "skipped", "reason": "already_claimed_or_terminal"}

        resume = ResumeRepository.get_by_id(db, resume_id)
        if not resume:
            logger.error(f"Claimed resume {resume_id} not found in database.")
            return {"status": "failed", "reason": "resume_not_found"}

        temp_key_to_delete = resume.temp_storage_key

        if not temp_key_to_delete:
            ResumeRepository.update_status(
                db=db,
                resume_id=resume.id,
                to_status=ResumeStatus.FAILED.value,
                failure_category="FILE_SYSTEM",
                failure_reason_code="STORAGE_KEY_MISSING",
                failure_message="Temporary storage reference is missing for resume.",
            )
            return {"status": "failed", "reason": "storage_key_missing"}

        storage_path = CleanupService.get_storage_path(temp_key_to_delete)
        if not storage_path.exists():
            ResumeRepository.update_status(
                db=db,
                resume_id=resume.id,
                to_status=ResumeStatus.FAILED.value,
                failure_category="FILE_SYSTEM",
                failure_reason_code="FILE_NOT_FOUND",
                failure_message="Stored temporary resume file was not found on disk.",
            )
            return {"status": "failed", "reason": "file_not_found"}

        # 2. Extract raw text
        outcome = DocumentLoader.load_file(str(storage_path))

        # Check for extraction failure (scanned / corrupted / unsupported)
        if outcome.status.value != "SUCCESS" or not outcome.raw_text:
            fail_code = (
                outcome.failure_code.value if outcome.failure_code else "DOCUMENT_UNREADABLE"
            )
            ResumeRepository.update_status(
                db=db,
                resume_id=resume.id,
                to_status=ResumeStatus.FAILED.value,
                failure_category="DOCUMENT_INTELLIGENCE",
                failure_reason_code=fail_code,
                failure_message=outcome.failure_message or "Unable to extract text.",
            )
            logger.info(f"Resume {resume_id} extraction failed: {fail_code}")
            return {"status": "failed", "reason": fail_code}

        # 3. Extract candidate structured profile
        candidate_data = ProfileExtractor.extract_profile(outcome.raw_text)
        candidate = CandidateRepository.create(db, analysis_id, resume_id, candidate_data)

        # 4. Build sanitized ScoringProfile (PII and demographics removed)
        scoring_profile = ProfileBuilder.build_scoring_profile(candidate_data)

        # 5. Fetch confirmed JobRequirements and build MatchingProfile
        req_model = JobRequirementsRepository.get_by_analysis_id(db, analysis_id)
        if not req_model:
            raise ValueError(f"Job requirements not found for analysis {analysis_id}")

        reqs = JobRequirements(
            required_skills=req_model.required_skills,
            preferred_skills=req_model.preferred_skills,
            experience_requirements=req_model.experience_requirements,
            education_requirements=req_model.education_requirements,
            explicit_requirements=req_model.explicit_requirements,
            job_relevant_text=req_model.job_relevant_text,
            confirmed_at=req_model.confirmed_at,
        )
        matching_profile = MatchingProfileBuilder.build_matching_profile(reqs)

        # 6. Index sanitized profile in analysis-isolated vector store
        default_vector_store.upsert_document(
            analysis_id=analysis_id,
            doc_id=candidate.id,
            text=scoring_profile.job_relevant_text,
        )

        # 7. Deterministic Multi-Component Scoring
        scoring_engine = ScoringEngine()
        match_result = scoring_engine.score_candidate(
            candidate.id, scoring_profile, matching_profile
        )

        # 8. Persist match result and update status to SUCCESS
        MatchResultRepository.save_or_update(db, analysis_id, match_result)
        ResumeRepository.update_status(
            db=db,
            resume_id=resume.id,
            to_status=ResumeStatus.SUCCESS.value,
        )

        logger.info(f"Resume {resume_id} processed successfully. Score: {match_result.match_score}")
        return {"status": "success", "candidate_id": candidate.id}

    except Exception as exc:
        logger.error(f"Unhandled error processing resume {resume_id}: {exc}")
        try:
            ResumeRepository.update_status(
                db=db,
                resume_id=resume_id,
                to_status=ResumeStatus.FAILED.value,
                failure_category="SYSTEM_ERROR",
                failure_reason_code="WORKER_EXCEPTION",
                failure_message="Internal error occurred while processing resume.",
            )
        except Exception:
            pass
        return {"status": "error", "message": str(exc)}

    finally:
        # Guaranteed raw-file deletion
        if temp_key_to_delete:
            CleanupService.delete_temporary_file(temp_key_to_delete)

        # Check and trigger finalization if all accepted resumes reached terminal state
        try:
            WatchdogService.finalize_analysis(db, analysis_id)
        except Exception as e:
            logger.warning(f"Error checking finalization from task: {e}")

        db.close()


@celery_app.task(name="backend.worker.tasks.finalize_analysis_task", queue="resume_queue")
def finalize_analysis_task(analysis_id: str) -> bool:
    """Asynchronous task to finalize and rank an analysis."""
    db = SessionLocal()
    try:
        return WatchdogService.finalize_analysis(db, analysis_id)
    finally:
        db.close()


@celery_app.task(name="backend.worker.tasks.periodic_watchdog_task", queue="resume_queue")
def periodic_watchdog_task() -> dict[str, int]:
    """Periodic task running watchdog recovery, retention cleanup, and sweeps."""
    db = SessionLocal()
    try:
        return WatchdogService.run_watchdog_cycle(db)
    finally:
        db.close()
