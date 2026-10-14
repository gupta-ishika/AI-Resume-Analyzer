from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.errors import ConflictError, NotFoundError
from backend.repositories.analysis_repo import AnalysisRepository
from backend.repositories.candidate_repo import CandidateRepository
from backend.repositories.explanation_repo import ExplanationRepository
from backend.repositories.matching_repo import MatchResultRepository
from backend.repositories.resume_repo import ResumeRepository
from backend.schemas.api import (
    CandidateDetailResponse,
    CandidateExplanationBlock,
    CandidateExtractedBlock,
    CandidateIdentityBlock,
    CandidateListResponse,
    CandidateMatchingBlock,
    ExcludedFileItem,
    RankedCandidateItem,
)
from backend.schemas.candidate import (
    CandidateContact,
    EducationItem,
    ExperienceItem,
    ProjectItem,
)
from backend.schemas.common import (
    AnalysisStatus,
    ExplanationState,
    ResumeStatus,
    ScoreComponent,
    ScoreComponentStatus,
)
from backend.schemas.matching import (
    ExperienceEvidenceItem,
    ScoreBreakdown,
    SkillMatchEvidence,
)

router = APIRouter(prefix="/analyses/{analysis_id}/candidates", tags=["Candidates"])


@router.get("", response_model=CandidateListResponse)
def list_candidates(analysis_id: str, db: Session = Depends(get_db)):
    """
    Returns ranked candidates without personal identity data.
    Allowed only when analysis is in RANKED status.
    Separately lists failed and needs-review files.
    """
    analysis = AnalysisRepository.get_by_id(db, analysis_id)
    if not analysis or analysis.deletion_requested_at is not None:
        raise NotFoundError("ANALYSIS_NOT_FOUND", "Analysis not found.")

    if analysis.status != AnalysisStatus.RANKED.value:
        raise ConflictError(
            "INVALID_ANALYSIS_STATE",
            (
                f"Candidates can only be viewed when analysis is RANKED. "
                f"Current status: '{analysis.status}'."
            ),
        )

    # 1. Fetch all match results with ranks
    match_results = MatchResultRepository.list_by_analysis(db, analysis_id)
    candidates_by_id = {c.id: c for c in CandidateRepository.list_by_analysis(db, analysis_id)}

    ranking: list[RankedCandidateItem] = []
    for res in match_results:
        cand = candidates_by_id.get(res.candidate_id)
        if not cand:
            continue

        comp_scores = res.component_scores or {}
        req_cov_data = comp_scores.get(
            "required_skill_coverage",
            {"status": ScoreComponentStatus.NOT_SPECIFIED.value, "value": None},
        )
        exp_data = comp_scores.get(
            "relevant_experience",
            {"status": ScoreComponentStatus.NOT_SPECIFIED.value, "value": None},
        )

        ranking.append(
            RankedCandidateItem(
                rank=res.rank or 0,
                candidate_id=cand.id,
                label=cand.display_label or "Unassigned",
                match_score=res.match_score,
                required_skill_coverage=ScoreComponent.model_validate(req_cov_data),
                relevant_experience=ScoreComponent.model_validate(exp_data),
            )
        )

    # 2. Separate excluded / failed / needs_review files
    resumes = ResumeRepository.list_by_analysis(db, analysis_id)
    excluded_files: list[ExcludedFileItem] = []
    for r in resumes:
        if r.status in (ResumeStatus.FAILED.value, ResumeStatus.NEEDS_REVIEW.value):
            excluded_files.append(
                ExcludedFileItem(
                    resume_id=r.id,
                    filename=r.original_filename,
                    status=r.status,
                    reason_code=r.failure_reason_code,
                    message=r.failure_message,
                )
            )

    return CandidateListResponse(
        analysis_id=analysis_id,
        status=AnalysisStatus(analysis.status),
        ranking=ranking,
        excluded_files=excluded_files,
    )


@router.get("/{candidate_id}", response_model=CandidateDetailResponse)
def get_candidate_detail(
    analysis_id: str,
    candidate_id: str,
    db: Session = Depends(get_db),
):
    """
    Returns the four separate candidate blocks:
    1. Identity: name and contact details (only shown here).
    2. Extracted: skills, experience, projects, education.
    3. Matching: score breakdown, matched/missing skills, evidence.
    4. Explanation: explanation generation state.
    Never returns raw resume text or files.
    """
    analysis = AnalysisRepository.get_by_id(db, analysis_id)
    if not analysis or analysis.deletion_requested_at is not None:
        raise NotFoundError("ANALYSIS_NOT_FOUND", "Analysis not found.")

    candidate = CandidateRepository.get_by_id(db, candidate_id)
    if not candidate or candidate.analysis_id != analysis_id:
        raise NotFoundError("CANDIDATE_NOT_FOUND", "Candidate not found.")

    match_result = MatchResultRepository.get_by_candidate_id(db, candidate_id)
    if not match_result:
        raise NotFoundError("MATCH_RESULT_NOT_FOUND", "Match result not found for candidate.")

    explanation_model = ExplanationRepository.get_by_candidate_id(db, candidate_id)
    expl_state = (
        ExplanationState(explanation_model.state)
        if explanation_model
        else ExplanationState.NOT_REQUESTED
    )

    # 1. Identity Block
    identity_block = CandidateIdentityBlock(
        name=candidate.candidate_name,
        contact=CandidateContact(
            email=candidate.contact_email,
            phone=candidate.contact_phone,
            other=candidate.contact_other or [],
        ),
    )

    # 2. Extracted Data Block
    extracted_block = CandidateExtractedBlock(
        skills=candidate.extracted_skills or [],
        experience=[ExperienceItem.model_validate(e) for e in candidate.extracted_experience or []],
        projects=[ProjectItem.model_validate(p) for p in candidate.extracted_projects or []],
        education=[EducationItem.model_validate(ed) for ed in candidate.extracted_education or []],
    )

    # 3. Matching Evidence Block
    matching_evidence = match_result.matching_evidence or {}
    matching_block = CandidateMatchingBlock(
        match_score=match_result.match_score,
        breakdown=ScoreBreakdown.model_validate(match_result.component_scores or {}),
        required_skills=SkillMatchEvidence.model_validate(
            matching_evidence.get("required_skills", {})
        ),
        preferred_skills=SkillMatchEvidence.model_validate(
            matching_evidence.get("preferred_skills", {})
        ),
        experience_evidence=[
            ExperienceEvidenceItem.model_validate(e)
            for e in matching_evidence.get("experience_evidence", [])
        ],
    )

    # 4. Explanation Block
    explanation_block = CandidateExplanationBlock(state=expl_state)

    return CandidateDetailResponse(
        candidate_id=candidate.id,
        label=candidate.display_label or "Candidate",
        rank=match_result.rank,
        identity=identity_block,
        extracted=extracted_block,
        matching=matching_block,
        explanation=explanation_block,
    )
