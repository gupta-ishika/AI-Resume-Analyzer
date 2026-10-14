import json
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.core.errors import ConflictError
from backend.repositories.analysis_repo import AnalysisRepository
from backend.repositories.candidate_repo import CandidateRepository
from backend.repositories.explanation_repo import ExplanationRepository
from backend.repositories.matching_repo import MatchResultRepository
from backend.repositories.requirements_repo import JobRequirementsRepository
from backend.schemas.candidate import (
    CandidateContact,
    CandidateExtractedData,
    CandidateIdentity,
    ExperienceItem,
)
from backend.schemas.common import (
    AnalysisStatus,
    EducationMatch,
    EducationMatchStatus,
    ExplanationState,
    ScoreComponent,
    ScoreComponentStatus,
)
from backend.schemas.explanation import ExplanationData
from backend.schemas.matching import (
    ExperienceEvidenceItem,
    MatchResultData,
    ScoreBreakdown,
    SkillMatchEvidence,
)
from backend.schemas.requirements import JobRequirements
from backend.services.explanation_grounding import ExplanationGroundingService
from backend.services.explanation_service import ExplanationService
from backend.services.llm_service import (
    LLMConnectionError,
    LLMResponseParseError,
    LLMTimeoutError,
    MockLLMService,
    OllamaLLMService,
)
from backend.services.watchdog_service import WatchdogService

# --- LLM-01 Grounding Tests ---


def test_explanation_grounding_valid():
    """LLM-01: Valid explanation grounded in actual candidate skills and gaps."""
    expl = ExplanationData(
        strengths=["Demonstrated expertise in Python and FastAPI backend architectures."],
        gaps=["Lacks experience with AWS cloud deployment."],
        experience_alignment="3 years of software engineering aligns with backend expectations.",
        assessment="Strong backend candidate with core required skills.",
    )

    is_valid, validated, violations = ExplanationGroundingService.validate_grounding(
        explanation=expl,
        candidate_skills=["Python", "FastAPI"],
        matched_skills=["Python", "FastAPI"],
        missing_required=["AWS"],
        missing_preferred=[],
        candidate_name="Alice Smith",
    )

    assert is_valid is True
    assert validated is not None
    assert len(violations) == 0
    assert len(validated.strengths) == 1
    assert len(validated.gaps) == 1


def test_explanation_grounding_hallucinated_skills_rejected():
    """LLM-01: Explanation citing completely hallucinated skills is rejected."""
    expl = ExplanationData(
        strengths=["Expert in Rust, Kubernetes, and Go programming."],
        gaps=["None"],
        experience_alignment="Extensive systems engineering experience.",
        assessment="Exceptional candidate.",
    )

    is_valid, validated, violations = ExplanationGroundingService.validate_grounding(
        explanation=expl,
        candidate_skills=["Python"],
        matched_skills=["Python"],
        missing_required=["FastAPI"],
        missing_preferred=[],
        candidate_name="Bob Jones",
    )

    assert is_valid is False
    assert validated is None
    assert any("Ungrounded" in v for v in violations)


def test_explanation_grounding_contradictory_gap_rejected():
    """LLM-01: Claiming a gap for a skill that was actually matched is rejected."""
    expl = ExplanationData(
        strengths=["Good general background."],
        gaps=["Candidate has no experience with Python."],  # Python was matched!
        experience_alignment="Some background.",
        assessment="Average fit.",
    )

    is_valid, validated, violations = ExplanationGroundingService.validate_grounding(
        explanation=expl,
        candidate_skills=["Python", "SQL"],
        matched_skills=["Python"],
        missing_required=["Docker"],
        missing_preferred=[],
        candidate_name="Charlie Brown",
    )

    assert is_valid is False
    assert any("Contradictory" in v for v in violations)


def test_explanation_grounding_pii_leakage_rejected():
    """LLM-01: Explanation containing candidate PII (name, email, phone) is rejected."""
    expl = ExplanationData(
        strengths=["Charlie Brown is skilled in Python."],
        gaps=[],
        experience_alignment="Aligns with backend role.",
        assessment="Candidate Charlie Brown is a solid fit. Contact at charlie@example.com.",
    )

    is_valid, validated, violations = ExplanationGroundingService.validate_grounding(
        explanation=expl,
        candidate_skills=["Python"],
        matched_skills=["Python"],
        missing_required=[],
        missing_preferred=[],
        candidate_name="Charlie Brown",
    )

    assert is_valid is False
    assert any("PII Leak" in v for v in violations)


# --- LLM-02 Ollama Adapter Tests ---


def test_ollama_service_adapter_success():
    """LLM-02: Test OllamaLLMService parses valid JSON response."""
    service = OllamaLLMService(base_url="http://localhost:11434", model="llama3.2:3b")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "response": json.dumps({
            "strengths": ["Strong Python skills"],
            "gaps": ["No Docker"],
            "experience_alignment": "Good",
            "assessment": "Recommended",
        })
    }

    with patch("httpx.Client.post", return_value=mock_resp):
        res = service.generate_explanation(prompt="test prompt")
        assert res["strengths"] == ["Strong Python skills"]
        assert res["gaps"] == ["No Docker"]


def test_ollama_service_adapter_error_handling():
    """LLM-02: Test explicit error types on connection error, timeout, and malformed json."""
    service = OllamaLLMService(base_url="http://localhost:11434")

    # 1. Connection error
    with patch("httpx.Client.post", side_effect=httpx.ConnectError("Connection refused")):
        with pytest.raises(LLMConnectionError):
            service.generate_explanation(prompt="test")

    # 2. Timeout error
    with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Timed out")):
        with pytest.raises(LLMTimeoutError):
            service.generate_explanation(prompt="test")

    # 3. Invalid JSON output
    mock_bad_resp = MagicMock()
    mock_bad_resp.status_code = 200
    mock_bad_resp.json.return_value = {"response": "Not valid json at all!"}
    with patch("httpx.Client.post", return_value=mock_bad_resp):
        with pytest.raises(LLMResponseParseError):
            service.generate_explanation(prompt="test")


# --- LLM-03 & LLM-04 Lifecycle, Invariance & API Tests ---


@pytest.fixture
def ranked_analysis_with_candidate(db_session: Session):
    """Sets up a RANKED analysis with a confirmed requirement and one scored candidate."""
    analysis = AnalysisRepository.create(db_session, name="Explanation Integration Test")

    # Job Requirements
    JobRequirementsRepository.save_or_update(
        db_session,
        analysis_id=analysis.id,
        reqs=JobRequirements(
            required_skills=["Python", "FastAPI"],
            preferred_skills=["Docker"],
            experience_requirements=["3+ years backend development"],
            education_requirements=[],
            explicit_requirements=[],
            confirmed_at=datetime.now(UTC),
        ),
    )

    # Candidate
    candidate = CandidateRepository.create(
        db_session,
        analysis_id=analysis.id,
        resume_id=f"resume-expl-{uuid.uuid4()}",
        data=CandidateExtractedData(
            identity=CandidateIdentity(
                name="Jane Doe",
                contact=CandidateContact(email="jane@example.com", phone="123-456-7890"),
            ),
            skills=["Python", "FastAPI", "SQL"],
            experience=[
                ExperienceItem(
                    title="Backend Engineer",
                    duration_months=36,
                    responsibilities=["Built REST APIs in Python"],
                )
            ],
            projects=[],
            education=[],
        ),
    )
    # Assign labels and ranks
    CandidateRepository.assign_labels_and_ranks(
        db=db_session,
        analysis_id=analysis.id,
        ranked_candidate_ids=[candidate.id],
    )

    # Match Result
    score_breakdown = ScoreBreakdown(
        required_skill_coverage=ScoreComponent(
            status=ScoreComponentStatus.SCORED, value=100.0
        ),
        preferred_skill_coverage=ScoreComponent(
            status=ScoreComponentStatus.SCORED, value=0.0
        ),
        semantic_relevance=ScoreComponent(
            status=ScoreComponentStatus.SCORED, value=85.0
        ),
        relevant_experience=ScoreComponent(
            status=ScoreComponentStatus.SCORED, value=80.0
        ),
        education=EducationMatch(status=EducationMatchStatus.NOT_SPECIFIED),
    )
    match_result_data = MatchResultData(
        candidate_id=candidate.id,
        match_score=83.5,
        rank=1,
        breakdown=score_breakdown,
        required_skills=SkillMatchEvidence(
            matched=["Python", "FastAPI"], missing=[]
        ),
        preferred_skills=SkillMatchEvidence(
            matched=[], missing=["Docker"]
        ),
        experience_evidence=[
            ExperienceEvidenceItem(summary="3 years backend development")
        ],
    )
    MatchResultRepository.save_or_update(db_session, analysis.id, match_result_data)

    # Transition to RANKED
    AnalysisRepository.update_status_conditional(
        db_session,
        analysis.id,
        from_status=AnalysisStatus.REQUIREMENTS_PENDING.value,
        to_status=AnalysisStatus.RANKED.value,
    )

    return analysis, candidate


def test_sanitized_prompt_excludes_pii(
    db_session: Session, ranked_analysis_with_candidate
):
    """LLM-01 / LLM-03: Verify prompt uses display label and never includes personal identifiers."""
    analysis, candidate = ranked_analysis_with_candidate
    match_result = MatchResultRepository.get_by_candidate_id(db_session, candidate.id)
    requirements = JobRequirementsRepository.get_by_analysis_id(db_session, analysis.id)

    system_prompt, user_prompt = ExplanationService.build_sanitized_prompt(
        candidate=candidate,
        match_result=match_result,
        requirements=requirements,
    )

    # Must contain display label
    assert "Candidate 01" in user_prompt
    # Must NOT contain personal name or contact info
    assert "Jane Doe" not in user_prompt
    assert "jane@example.com" not in user_prompt
    assert "123-456-7890" not in user_prompt


def test_explanation_request_cannot_start_unless_ranked(db_session: Session):
    """LLM-03: Explanations cannot be requested if analysis is not RANKED."""
    analysis = AnalysisRepository.create(db_session, name="Pending Analysis")
    candidate = CandidateRepository.create(
        db_session,
        analysis.id,
        f"res-{uuid.uuid4()}",
        data=CandidateExtractedData(
            identity=CandidateIdentity(name="Test Candidate"),
            skills=[],
        ),
    )

    with pytest.raises(ConflictError) as exc_info:
        ExplanationService.request_explanation(db_session, analysis.id, candidate.id)
    assert exc_info.value.code == "ANALYSIS_NOT_RANKED"


def test_explanation_lifecycle_and_api_endpoints(
    client: TestClient, db_session: Session, ranked_analysis_with_candidate
):
    """
    LLM-03 & LLM-04: Test full lifecycle via API:
    NOT_REQUESTED -> POST (GENERATING) -> READY -> POST (no regeneration)
    """
    analysis, candidate = ranked_analysis_with_candidate
    url = f"/api/analyses/{analysis.id}/candidates/{candidate.id}/explanation"

    # 1. Initial GET -> NOT_REQUESTED
    get_resp = client.get(url)
    assert get_resp.status_code == 200
    assert get_resp.json()["state"] == "NOT_REQUESTED"
    assert get_resp.json()["explanation"] is None

    # 2. Mock LLM service for asynchronous worker execution
    mock_llm = MockLLMService(
        canned_response={
            "strengths": ["Strong proficiency in Python and FastAPI."],
            "gaps": ["No evidence of Docker containerization."],
            "experience_alignment": "3 years of backend experience directly satisfies requirement.",
            "assessment": "Top-tier candidate meeting all required technical specifications.",
        }
    )

    # In eager Celery test mode, POST triggers task immediately
    with patch("backend.services.explanation_service.default_llm_service", mock_llm):
        post_resp = client.post(url)
        assert post_resp.status_code == 200

    # 3. GET should now return READY with validated content
    get_ready_resp = client.get(url)
    assert get_ready_resp.status_code == 200
    ready_data = get_ready_resp.json()
    assert ready_data["state"] == "READY"
    assert ready_data["explanation"] is not None
    assert "Python" in ready_data["explanation"]["strengths"][0]

    # 4. Subsequent POST when already READY returns READY and does not regenerate
    with patch.object(mock_llm, "generate_explanation") as mock_gen:
        post_again = client.post(url)
        assert post_again.status_code == 200
        assert post_again.json()["state"] == "READY"
        mock_gen.assert_not_called()


def test_explanation_failure_and_score_invariance(
    client: TestClient, db_session: Session, ranked_analysis_with_candidate
):
    """
    LLM-03 / LLM-04: Failed explanation moves to FAILED, does NOT affect candidate score/rank,
    and allows retry.
    """
    analysis, candidate = ranked_analysis_with_candidate
    url = f"/api/analyses/{analysis.id}/candidates/{candidate.id}/explanation"

    # Initial score and rank
    initial_match = MatchResultRepository.get_by_candidate_id(db_session, candidate.id)
    initial_score = initial_match.match_score
    initial_rank = initial_match.rank

    # 1. Trigger failure via simulated connection error
    failing_llm = MockLLMService(
        should_fail=True,
        failure_exc=LLMConnectionError("Could not connect to Ollama service"),
    )
    with patch("backend.services.explanation_service.default_llm_service", failing_llm):
        post_resp = client.post(url)
        assert post_resp.status_code == 200

    # 2. GET returns FAILED state with failure reason
    failed_resp = client.get(url)
    assert failed_resp.status_code == 200
    assert failed_resp.json()["state"] == "FAILED"
    assert "Could not connect to Ollama" in failed_resp.json()["failure_reason"]

    # 3. Verify Score Invariance: Score and rank are completely unchanged!
    db_session.expire_all()
    post_match = MatchResultRepository.get_by_candidate_id(db_session, candidate.id)
    assert post_match.match_score == initial_score
    assert post_match.rank == initial_rank

    # Candidate detail endpoint also reports FAILED explanation block without altering matching data
    detail_resp = client.get(f"/api/analyses/{analysis.id}/candidates/{candidate.id}")
    assert detail_resp.status_code == 200
    detail_json = detail_resp.json()
    assert detail_json["matching"]["match_score"] == initial_score
    assert detail_json["explanation"]["state"] == "FAILED"

    # 4. Retry after FAILED is allowed: with working LLM, it succeeds!
    working_llm = MockLLMService()
    with patch("backend.services.explanation_service.default_llm_service", working_llm):
        retry_resp = client.post(url)
        assert retry_resp.status_code == 200

    ready_resp = client.get(url)
    assert ready_resp.status_code == 200
    assert ready_resp.json()["state"] == "READY"


def test_watchdog_reclaims_stale_generating_explanation(
    db_session: Session, ranked_analysis_with_candidate
):
    """LLM-03 / BG-05: Watchdog cycle reclaims stuck GENERATING explanations to FAILED."""
    analysis, candidate = ranked_analysis_with_candidate

    # Manually start generation in the past
    ExplanationRepository.start_generation_conditional(
        db_session, candidate.id, analysis.id
    )
    # Move generation_started_at back 300 seconds
    from backend.repositories.models import ExplanationModel

    old_time = datetime.now(UTC) - timedelta(seconds=300)
    db_session.query(ExplanationModel).filter_by(candidate_id=candidate.id).update(
        {"generation_started_at": old_time}
    )
    db_session.commit()

    # Run watchdog cycle
    stats = WatchdogService.run_watchdog_cycle(db_session)
    assert stats["stale_explanations_reclaimed"] == 1

    # Verify model is now FAILED
    expl = ExplanationRepository.get_by_candidate_id(db_session, candidate.id)
    assert expl.state == ExplanationState.FAILED.value
    assert expl.failure_reason == "EXPLANATION_TIMEOUT"
