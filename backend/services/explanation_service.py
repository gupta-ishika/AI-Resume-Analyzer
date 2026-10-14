import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from backend.core.errors import ConflictError, NotFoundError
from backend.core.logging import get_logger
from backend.repositories.analysis_repo import AnalysisRepository
from backend.repositories.candidate_repo import CandidateRepository
from backend.repositories.explanation_repo import ExplanationRepository
from backend.repositories.matching_repo import MatchResultRepository
from backend.repositories.models import CandidateModel, JobRequirementsModel, MatchResultModel
from backend.repositories.requirements_repo import JobRequirementsRepository
from backend.schemas.common import AnalysisStatus, ExplanationState
from backend.schemas.explanation import ExplanationData, ExplanationResponse
from backend.services.explanation_grounding import ExplanationGroundingService
from backend.services.llm_service import LLMService, default_llm_service
from backend.services.pii_scrubber import PIIScrubber

logger = get_logger("explanation_service")


class ExplanationService:
    """
    Coordinates AI Explanation request lifecycle, prompt generation, LLM execution,
    grounding validation, and atomic state updates (LLM-01 through LLM-04).
    """

    @classmethod
    def build_sanitized_prompt(
        cls,
        candidate: CandidateModel,
        match_result: MatchResultModel,
        requirements: JobRequirementsModel,
    ) -> tuple[str, str]:
        """
        Builds a privacy-safe, grounded prompt and system prompt.
        Guarantees that no candidate names, contact details, or demographic info
        are sent to the LLM.
        """
        system_prompt = (
            "You are an objective AI recruitment assistant for a resume matching system. "
            "Your task is to provide an evidence-based explanation comparing a candidate "
            "to the role.\n\n"
            "CRITICAL RULES:\n"
            "1. Ground your analysis strictly in matching evidence and candidate structured data.\n"
            "2. NEVER invent qualifications, skills, or achievements not explicitly listed.\n"
            "3. NEVER decide whether to hire, calculate or modify scores, or re-rank candidates.\n"
            "4. NEVER mention personal names, emails, phones, or demographics. "
            "Refer to the applicant ONLY by their assigned identifier.\n"
            "5. If information or skill is missing or unverified, state it explicitly.\n"
            "6. Output MUST be strictly valid JSON with the following structure:\n"
            "   {\n"
            '     "strengths": ["string", ...],\n'
            '     "gaps": ["string", ...],\n'
            '     "experience_alignment": "string",\n'
            '     "assessment": "string"\n'
            "   }"
        )

        display_label = candidate.display_label or "Candidate"
        matching_evidence = match_result.matching_evidence or {}
        req_skills_data = matching_evidence.get("required_skills", {})
        pref_skills_data = matching_evidence.get("preferred_skills", {})

        # Sanitize candidate experiences (remove institution names)
        sanitized_experiences: list[dict[str, Any]] = []
        for exp in candidate.extracted_experience or []:
            sanitized_exp = {
                "title": exp.get("title", "Role"),
                "duration_months": exp.get("duration_months"),
                "start_date": exp.get("start_date"),
                "end_date": exp.get("end_date"),
                "responsibilities": [
                    PIIScrubber.scrub_text(
                        r,
                        name=candidate.candidate_name,
                        email=candidate.contact_email,
                        phone=candidate.contact_phone,
                    )
                    for r in exp.get("responsibilities", [])
                ],
            }
            sanitized_experiences.append(sanitized_exp)

        user_prompt_data = {
            "candidate_identifier": display_label,
            "overall_match_score": f"{match_result.match_score:.1f}/100",
            "component_scores": match_result.component_scores,
            "requirements": {
                "required_skills": requirements.required_skills,
                "preferred_skills": requirements.preferred_skills,
                "experience_requirements": requirements.experience_requirements,
                "education_requirements": requirements.education_requirements,
                "explicit_requirements": requirements.explicit_requirements,
            },
            "candidate_matching_evidence": {
                "matched_required_skills": req_skills_data.get("matched_skills", []),
                "missing_required_skills": req_skills_data.get("missing_skills", []),
                "matched_preferred_skills": pref_skills_data.get("matched_skills", []),
                "missing_preferred_skills": pref_skills_data.get("missing_skills", []),
                "candidate_extracted_skills": candidate.extracted_skills or [],
                "relevant_experience_evidence": matching_evidence.get("experience_evidence", []),
                "work_history": sanitized_experiences,
            },
        }

        user_prompt = (
            f"Generate an explanation for {display_label} using this ground truth data:\n\n"
            f"{json.dumps(user_prompt_data, indent=2)}\n\n"
            "Return valid JSON adhering to the specified schema."
        )

        return system_prompt, user_prompt

    @classmethod
    def request_explanation(
        cls,
        db: Session,
        analysis_id: str,
        candidate_id: str,
    ) -> ExplanationResponse:
        """
        API-facing handler for POST /api/analyses/{id}/candidates/{candidate_id}/explanation.
        Enforces state rules:
        - Only allowed when analysis is in RANKED status.
        - Atomic transition from NOT_REQUESTED or FAILED to GENERATING.
        - Existing GENERATING or READY returns current state without re-enqueuing.
        - READY explanation cannot be regenerated.
        """
        analysis = AnalysisRepository.get_by_id(db, analysis_id)
        if not analysis or analysis.deletion_requested_at is not None:
            raise NotFoundError("ANALYSIS_NOT_FOUND", "Analysis not found.")

        if analysis.status != AnalysisStatus.RANKED.value:
            raise ConflictError(
                "ANALYSIS_NOT_RANKED",
                f"Explanations require 'RANKED' status. Current: '{analysis.status}'.",
            )

        candidate = CandidateRepository.get_by_id(db, candidate_id)
        if not candidate or candidate.analysis_id != analysis_id:
            raise NotFoundError("CANDIDATE_NOT_FOUND", "Candidate not found in this analysis.")

        existing = ExplanationRepository.get_by_candidate_id(db, candidate_id)

        # If already READY: return without regeneration (per MVP rules)
        if existing and existing.state == ExplanationState.READY.value:
            expl_data = (
                ExplanationData.model_validate(existing.explanation_content)
                if existing.explanation_content
                else None
            )
            return ExplanationResponse(
                state=ExplanationState.READY,
                explanation=expl_data,
            )

        # If already GENERATING: return without duplicate task enqueue
        if existing and existing.state == ExplanationState.GENERATING.value:
            return ExplanationResponse(state=ExplanationState.GENERATING)

        # Atomic transition to GENERATING
        transitioned = ExplanationRepository.start_generation_conditional(
            db, candidate_id=candidate_id, analysis_id=analysis_id
        )

        if not transitioned:
            # Race condition, re-read state
            current = ExplanationRepository.get_by_candidate_id(db, candidate_id)
            curr_state = (
                ExplanationState(current.state) if current else ExplanationState.NOT_REQUESTED
            )
            return ExplanationResponse(state=curr_state)

        # Dispatch async Celery task to the explanation queue
        from backend.worker.tasks import generate_explanation_task

        generate_explanation_task.delay(analysis_id, candidate_id)

        return ExplanationResponse(state=ExplanationState.GENERATING)

    @classmethod
    def get_explanation(
        cls,
        db: Session,
        analysis_id: str,
        candidate_id: str,
    ) -> ExplanationResponse:
        """
        API-facing handler for GET /api/analyses/{id}/candidates/{candidate_id}/explanation.
        """
        analysis = AnalysisRepository.get_by_id(db, analysis_id)
        if not analysis or analysis.deletion_requested_at is not None:
            raise NotFoundError("ANALYSIS_NOT_FOUND", "Analysis not found.")

        candidate = CandidateRepository.get_by_id(db, candidate_id)
        if not candidate or candidate.analysis_id != analysis_id:
            raise NotFoundError("CANDIDATE_NOT_FOUND", "Candidate not found in this analysis.")

        model = ExplanationRepository.get_by_candidate_id(db, candidate_id)
        if not model:
            return ExplanationResponse(state=ExplanationState.NOT_REQUESTED)

        state = ExplanationState(model.state)
        expl_data: ExplanationData | None = None
        if state == ExplanationState.READY and model.explanation_content:
            try:
                expl_data = ExplanationData.model_validate(model.explanation_content)
            except Exception as e:
                logger.error(f"Error parsing stored explanation content: {e}")

        return ExplanationResponse(
            state=state,
            explanation=expl_data,
            failure_reason=model.failure_reason,
        )

    @classmethod
    def generate_and_save_explanation(
        cls,
        db: Session,
        analysis_id: str,
        candidate_id: str,
        llm_service: LLMService | None = None,
    ) -> None:
        """
        Worker-facing routine executed by Celery on the explanation queue.
        Fetches ground truth data, invokes LLM, validates output and grounding,
        and atomically updates explanation persistence.
        """
        service = llm_service or default_llm_service

        candidate = CandidateRepository.get_by_id(db, candidate_id)
        if not candidate:
            logger.error(f"Cannot generate explanation: Candidate {candidate_id} not found.")
            ExplanationRepository.mark_failed(db, candidate_id, "Candidate record not found.")
            return

        match_result = MatchResultRepository.get_by_candidate_id(db, candidate_id)
        if not match_result:
            logger.error(f"Cannot generate explanation: Match result for {candidate_id} not found.")
            ExplanationRepository.mark_failed(db, candidate_id, "Match result not found.")
            return

        requirements = JobRequirementsRepository.get_by_analysis_id(db, analysis_id)
        if not requirements:
            logger.error(f"Cannot generate explanation: Requirements for {analysis_id} not found.")
            ExplanationRepository.mark_failed(db, candidate_id, "Job requirements not found.")
            return

        try:
            # 1. Build sanitized prompt
            system_prompt, user_prompt = cls.build_sanitized_prompt(
                candidate=candidate,
                match_result=match_result,
                requirements=requirements,
            )

            # 2. Invoke LLM
            raw_dict = service.generate_explanation(
                prompt=user_prompt, system_prompt=system_prompt
            )

            # 3. Schema validation
            explanation_data = ExplanationData(
                strengths=raw_dict.get("strengths", []),
                gaps=raw_dict.get("gaps", []),
                experience_alignment=raw_dict.get("experience_alignment", ""),
                assessment=raw_dict.get("assessment", ""),
                generated_at=datetime.now(UTC),
            )

            # 4. Grounding validation
            matching_evidence = match_result.matching_evidence or {}
            req_matched = matching_evidence.get("required_skills", {}).get("matched_skills", [])
            req_missing = matching_evidence.get("required_skills", {}).get("missing_skills", [])
            pref_matched = matching_evidence.get("preferred_skills", {}).get("matched_skills", [])
            pref_missing = matching_evidence.get("preferred_skills", {}).get("missing_skills", [])

            all_matched = list(set(req_matched + pref_matched))
            candidate_skills = candidate.extracted_skills or []

            is_valid, validated_explanation, violations = (
                ExplanationGroundingService.validate_grounding(
                    explanation=explanation_data,
                    candidate_skills=candidate_skills,
                    matched_skills=all_matched,
                    missing_required=req_missing,
                    missing_preferred=pref_missing,
                    candidate_name=candidate.candidate_name,
                )
            )

            if not is_valid or not validated_explanation:
                reason = f"Grounding validation failed: {'; '.join(violations)}"
                logger.warning(
                    f"Explanation grounding failed for candidate {candidate_id}: {reason}"
                )
                ExplanationRepository.mark_failed(db, candidate_id, reason)
                return

            # 5. Persist validated explanation (state -> READY)
            ExplanationRepository.save_explanation(
                db, candidate_id, validated_explanation.model_dump(mode="json")
            )
            logger.info(f"Explanation saved for candidate {candidate_id}")

        except Exception as exc:
            error_msg = f"Explanation generation failed: {str(exc)}"
            logger.error(f"Error in explanation generation task for {candidate_id}: {exc}")
            try:
                ExplanationRepository.mark_failed(db, candidate_id, error_msg)
            except Exception as e:
                logger.error(f"Failed to mark explanation as failed: {e}")
