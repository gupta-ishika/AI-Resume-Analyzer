from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.logging import get_logger
from backend.repositories.analysis_repo import AnalysisRepository
from backend.repositories.matching_repo import MatchResultRepository
from backend.repositories.models import AnalysisModel
from backend.repositories.resume_repo import ResumeRepository
from backend.schemas.common import AnalysisStatus, ResumeStatus
from backend.schemas.matching import (
    ExperienceEvidenceItem,
    MatchResultData,
    ScoreBreakdown,
    SkillMatchEvidence,
)
from backend.services.cleanup_service import CleanupService
from backend.services.ranking_service import RankingService

logger = get_logger("watchdog_service")


class WatchdogService:
    """
    Coordinates finalization, failure recovery, stale task reclamation,
    and periodic system hygiene.
    Owned by Person 2 per ARCHITECTURE.md and TASKS.md BG-05.
    """

    @classmethod
    def finalize_analysis(
        cls,
        db: Session,
        analysis_id: str,
        max_retries: int = 2,
    ) -> bool:
        """
        Executes finalization inside a safe transaction:
        1. Checks that analysis is in PROCESSING status.
        2. Verifies all accepted resumes have reached terminal status.
        3. Persists final ranks and anonymous Candidate labels (Candidate 01, etc.).
        4. Transitions Analysis to RANKED.
        5. Handles retries with backoff; on exhaustion marks analysis FAILED.
        """
        analysis = db.scalar(select(AnalysisModel).where(AnalysisModel.id == analysis_id))
        if not analysis or analysis.status != AnalysisStatus.PROCESSING.value:
            return False

        # Verify all accepted resumes are terminal
        accepted_resumes = ResumeRepository.list_accepted(db, analysis_id)
        if not accepted_resumes:
            # No resumes accepted, mark RANKED with empty ranking
            AnalysisRepository.update_status_conditional(
                db,
                analysis_id,
                from_status=AnalysisStatus.PROCESSING.value,
                to_status=AnalysisStatus.RANKED.value,
            )
            return True

        non_terminal = [
            r for r in accepted_resumes
            if r.status in (ResumeStatus.READY.value, ResumeStatus.PROCESSING.value)
        ]
        if non_terminal:
            logger.info(
                f"Analysis {analysis_id} not ready for finalization; "
                f"{len(non_terminal)} resumes still pending."
            )
            return False

        # All resumes are terminal. Check if any succeeded.
        successful_resumes = [
            r for r in accepted_resumes if r.status == ResumeStatus.SUCCESS.value
        ]

        if not successful_resumes:
            # If all resumes failed/need-review, produce empty ranking and set to RANKED
            logger.info(
                f"All {len(accepted_resumes)} resumes failed for analysis {analysis_id}. "
                "Finalizing as empty RANKED."
            )
            AnalysisRepository.update_status_conditional(
                db,
                analysis_id,
                from_status=AnalysisStatus.PROCESSING.value,
                to_status=AnalysisStatus.RANKED.value,
            )
            return True

        # Fetch match results for ranking
        attempts = 0
        while attempts <= max_retries:
            try:
                results_models = MatchResultRepository.list_by_analysis(db, analysis_id)
                results_data: list[MatchResultData] = []
                for m in results_models:
                    data = MatchResultData(
                        candidate_id=m.candidate_id,
                        match_score=m.match_score,
                        rank=m.rank,
                        breakdown=ScoreBreakdown.model_validate(m.component_scores),
                        required_skills=SkillMatchEvidence.model_validate(
                            m.matching_evidence.get("required_skills", {})
                        ),
                        preferred_skills=SkillMatchEvidence.model_validate(
                            m.matching_evidence.get("preferred_skills", {})
                        ),
                        experience_evidence=[
                            ExperienceEvidenceItem.model_validate(e)
                            for e in m.matching_evidence.get("experience_evidence", [])
                        ],
                        config_version=m.scoring_config_version,
                    )
                    results_data.append(data)

                # Rank and assign labels
                RankingService.finalize_analysis_ranking(db, analysis_id, results_data)
                logger.info(
                    f"Successfully finalized and ranked analysis {analysis_id} "
                    f"with {len(results_data)} candidates."
                )
                return True
            except Exception as e:
                attempts += 1
                logger.warning(
                    f"Finalization attempt {attempts} failed for analysis {analysis_id}: {e}"
                )
                if attempts > max_retries:
                    logger.error(
                        f"All finalization retries exhausted for analysis {analysis_id}. "
                        "Marking analysis FAILED."
                    )
                    AnalysisRepository.update_status_conditional(
                        db,
                        analysis_id,
                        from_status=AnalysisStatus.PROCESSING.value,
                        to_status=AnalysisStatus.FAILED.value,
                        failure_reason="FINALIZATION_FAILED",
                    )
                    return False

        return False

    @classmethod
    def run_watchdog_cycle(cls, db: Session) -> dict[str, int]:
        """
        Executes a complete watchdog and recovery maintenance cycle:
        1. Recovers lost finalizations (analyses stuck in PROCESSING with all resumes terminal).
        2. Re-queues unclaimed READY resumes in PROCESSING analyses.
        3. Reclaims stale PROCESSING resumes (exceeding timeout).
        4. Sweeps expired uploads in REQUIREMENTS_PENDING analyses.
        5. Sweeps orphaned files and pending deletions.
        """
        stats: dict[str, int] = {
            "lost_finalizations_recovered": 0,
            "unclaimed_ready_requeued": 0,
            "stale_processing_reset": 0,
            "stale_processing_failed": 0,
            "expired_uploads_cleaned": 0,
            "orphaned_files_removed": 0,
            "pending_deletions_swept": 0,
        }

        # 1. Recover lost finalizations
        processing_analyses = list(
            db.scalars(
                select(AnalysisModel).where(
                    AnalysisModel.status == AnalysisStatus.PROCESSING.value,
                    AnalysisModel.deletion_requested_at.is_(None),
                )
            ).all()
        )

        for analysis in processing_analyses:
            accepted = ResumeRepository.list_accepted(db, analysis.id)
            if accepted:
                pending = [
                    r for r in accepted
                    if r.status in (ResumeStatus.READY.value, ResumeStatus.PROCESSING.value)
                ]
                if not pending:
                    # All resumes are terminal, but analysis is still PROCESSING
                    success = cls.finalize_analysis(db, analysis.id)
                    if success:
                        stats["lost_finalizations_recovered"] += 1

        # 2. Re-queue unclaimed READY resumes
        unclaimed = ResumeRepository.list_unclaimed_ready(
            db, max_age_seconds=settings.RESUME_CLAIM_TIMEOUT_SECONDS
        )
        for r in unclaimed:
            from backend.worker.tasks import process_resume_task
            try:
                process_resume_task.delay(r.analysis_id, r.id)
                stats["unclaimed_ready_requeued"] += 1
            except Exception as e:
                logger.warning(f"Could not re-queue unclaimed resume {r.id}: {e}")

        # 3. Handle stale PROCESSING resumes
        stale = ResumeRepository.list_stale_processing(
            db, max_age_seconds=settings.RESUME_CLAIM_TIMEOUT_SECONDS
        )
        for r in stale:
            if r.retry_count < 3:
                ResumeRepository.reset_to_ready_with_retry(db, r.id)
                from backend.worker.tasks import process_resume_task
                try:
                    process_resume_task.delay(r.analysis_id, r.id)
                    stats["stale_processing_reset"] += 1
                except Exception as e:
                    logger.warning(f"Could not re-queue reset resume {r.id}: {e}")
            else:
                ResumeRepository.update_status(
                    db=db,
                    resume_id=r.id,
                    to_status=ResumeStatus.FAILED.value,
                    failure_category="TIMEOUT",
                    failure_reason_code="PROCESSING_TIMEOUT",
                    failure_message="Resume exceeded maximum processing retry attempts.",
                )
                stats["stale_processing_failed"] += 1

        # 4. Clean expired uploads & orphaned files
        stats["expired_uploads_cleaned"] = CleanupService.cleanup_expired_pending_resumes(db)
        stats["orphaned_files_removed"] = CleanupService.cleanup_orphaned_temporary_files(db)
        stats["pending_deletions_swept"] = CleanupService.sweep_pending_deletions(db)

        return stats
