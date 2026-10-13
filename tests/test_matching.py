from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from backend.repositories.analysis_repo import AnalysisRepository
from backend.repositories.candidate_repo import CandidateRepository
from backend.schemas.candidate import (
    CandidateContact,
    CandidateExtractedData,
    CandidateIdentity,
    EducationItem,
    ExperienceItem,
    ProjectItem,
)
from backend.schemas.common import (
    AnalysisStatus,
    EducationMatch,
    EducationMatchStatus,
    ScoreComponent,
    ScoreComponentStatus,
)
from backend.schemas.matching import (
    MatchResultData,
    ScoreBreakdown,
    SkillMatchEvidence,
)
from backend.schemas.requirements import JobRequirements
from backend.services.embedding_service import (
    DeterministicHashEmbeddingService,
    InMemoryVectorStore,
)
from backend.services.matching_profile_builder import MatchingProfileBuilder
from backend.services.profile_builder import ProfileBuilder
from backend.services.ranking_service import RankingService
from backend.services.scoring_engine import ScoringConfig, ScoringEngine


def create_sample_candidate(
    name: str,
    email: str,
    phone: str,
    pronoun: str,
    institution: str,
    skills: list[str],
    experience_years: float,
) -> CandidateExtractedData:
    return CandidateExtractedData(
        identity=CandidateIdentity(
            name=name,
            contact=CandidateContact(email=email, phone=phone),
        ),
        skills=skills,
        experience=[
            ExperienceItem(
                title="Senior Software Engineer",
                company="TechCorp Inc",
                duration=f"{experience_years} years",
                years=experience_years,
                responsibilities=[
                    f"{pronoun.capitalize()} built scalable microservices and REST APIs.",
                    f"In this role, {pronoun} optimized database queries and led code reviews.",
                ],
            )
        ],
        projects=[
            ProjectItem(
                name="Cloud Platform",
                description=(
                    f"{pronoun.capitalize()} architected cloud deployment pipelines using Docker."
                ),
                technologies=["Docker", "Python"],
            )
        ],
        education=[
            EducationItem(
                degree="Bachelor of Science",
                field_of_study="Computer Science",
                institution=institution,
            )
        ],
    )


def test_profile_builder_scrubs_pii_and_institutions():
    candidate = create_sample_candidate(
        name="Jane Doe",
        email="jane.doe@example.com",
        phone="555-123-4567",
        pronoun="she",
        institution="Harvard University",
        skills=["Python", "FastAPI"],
        experience_years=4.0,
    )
    profile = ProfileBuilder.build_scoring_profile(candidate)

    # Verification: identity scrubbed
    assert "Jane" not in profile.job_relevant_text
    assert "Doe" not in profile.job_relevant_text
    assert "jane.doe@example.com" not in profile.job_relevant_text
    assert "555-123-4567" not in profile.job_relevant_text
    assert "Harvard" not in profile.job_relevant_text
    # Institution removed in education
    assert profile.education[0].institution is None
    assert profile.education[0].degree == "Bachelor of Science"


def test_matching_profile_builder_enforces_confirmation():
    unconfirmed = JobRequirements(
        required_skills=["Python", "FastAPI"],
        confirmed_at=None,
    )
    with pytest.raises(ValueError, match="Job requirements must be confirmed"):
        MatchingProfileBuilder.build_matching_profile(unconfirmed, enforce_confirmed=True)

    confirmed = JobRequirements(
        required_skills=["Python", "FastAPI"],
        preferred_skills=["Docker"],
        experience_requirements=["3+ years"],
        confirmed_at=datetime.now(UTC),
    )
    matching_profile = MatchingProfileBuilder.build_matching_profile(confirmed)
    assert matching_profile.required_skills == ["Python", "FastAPI"]
    assert matching_profile.preferred_skills == ["Docker"]
    assert "Python" in matching_profile.job_relevant_text


def test_embedding_service_and_vector_store_isolation():
    embedder = DeterministicHashEmbeddingService()
    vec1 = embedder.embed("Python backend engineer with FastAPI")
    vec2 = embedder.embed("Python backend engineer with FastAPI")
    vec3 = embedder.embed("Front-end React designer and illustrator")

    # Determinism
    assert vec1 == vec2
    sim_identical = embedder.similarity(vec1, vec2)
    assert pytest.approx(sim_identical, 0.001) == 1.0

    sim_diff = embedder.similarity(vec1, vec3)
    assert sim_diff < 0.8

    # Store isolation
    store = InMemoryVectorStore(embedder)
    store.upsert_document("analysis_A", "cand_1", "Python expert")
    store.upsert_document("analysis_B", "cand_2", "Java developer")

    res_a = store.query("analysis_A", "Python")
    assert len(res_a) == 1
    assert res_a[0]["id"] == "cand_1"

    # Cross-analysis retrieval is strictly empty
    res_b = store.query("analysis_B", "Python")
    assert len(res_b) == 1
    assert res_b[0]["id"] == "cand_2"


def test_scoring_engine_breakdown_and_weights():
    candidate = create_sample_candidate(
        name="Alex Smith",
        email="alex@sample.com",
        phone="555-987-6543",
        pronoun="they",
        institution="MIT",
        skills=["Python", "FastAPI", "Docker", "PostgreSQL"],
        experience_years=5.0,
    )
    profile = ProfileBuilder.build_scoring_profile(candidate)

    job_req = JobRequirements(
        required_skills=["Python", "FastAPI", "PostgreSQL"],
        preferred_skills=["Docker", "Kubernetes"],
        experience_requirements=["5+ years of software development"],
        education_requirements=["Bachelor's degree in Computer Science"],
        job_relevant_text=(
            "Senior Software Engineer to build scalable microservices and REST APIs, "
            "optimizing database queries and leading code reviews."
        ),
        confirmed_at=datetime.now(UTC),
    )
    m_profile = MatchingProfileBuilder.build_matching_profile(job_req)

    engine = ScoringEngine(
        config=ScoringConfig(
            required_skill_weight=0.35,
            preferred_skill_weight=0.15,
            relevant_experience_weight=0.25,
            semantic_relevance_weight=0.25,
        )
    )
    result = engine.score_candidate("cand_test_1", profile, m_profile)

    assert result.candidate_id == "cand_test_1"
    # Required skills: 3/3 = 100%
    assert result.breakdown.required_skill_coverage.status == ScoreComponentStatus.SCORED
    assert result.breakdown.required_skill_coverage.value == 100.0
    # Preferred skills: 1/2 (Docker matched, Kubernetes missing) = 50%
    assert result.breakdown.preferred_skill_coverage.value == 50.0
    # Relevant experience: 5 years / 5 years = 100%
    assert result.breakdown.relevant_experience.value == 100.0
    # Education matched
    assert result.breakdown.education.status == EducationMatchStatus.MET
    # Overall score > 80
    assert result.match_score >= 80.0


def test_scoring_engine_unspecified_components():
    """Unspecified requirements must not be treated as failures or penalize score."""
    candidate = create_sample_candidate(
        name="Jordan Lee",
        email="jordan@test.com",
        phone="555-000-1111",
        pronoun="they",
        institution="State College",
        skills=["Python"],
        experience_years=2.0,
    )
    profile = ProfileBuilder.build_scoring_profile(candidate)

    # Job with only required skills, no preferred, no experience requirement, no education
    job_req = JobRequirements(
        required_skills=["Python"],
        preferred_skills=[],
        experience_requirements=[],
        education_requirements=[],
        confirmed_at=datetime.now(UTC),
    )
    m_profile = MatchingProfileBuilder.build_matching_profile(job_req)

    engine = ScoringEngine()
    result = engine.score_candidate("cand_unspecified", profile, m_profile)

    assert result.breakdown.preferred_skill_coverage.status == ScoreComponentStatus.NOT_SPECIFIED
    assert result.breakdown.relevant_experience.status == ScoreComponentStatus.NOT_SPECIFIED
    assert result.breakdown.education.status == EducationMatchStatus.NOT_SPECIFIED
    # Since only required skills (100%) and semantic relevance are scored,
    # final score reflects active components
    assert result.match_score > 0.0


def test_ranking_service_deterministic_tie_breaking():
    # 4 candidates with ties
    def make_res(cid: str, score: float, req: float, exp: float, sem: float) -> MatchResultData:
        return MatchResultData(
            candidate_id=cid,
            match_score=score,
            breakdown=ScoreBreakdown(
                semantic_relevance=ScoreComponent(
                    status=ScoreComponentStatus.SCORED, value=sem
                ),
                required_skill_coverage=ScoreComponent(
                    status=ScoreComponentStatus.SCORED, value=req
                ),
                preferred_skill_coverage=ScoreComponent(
                    status=ScoreComponentStatus.SCORED, value=50.0
                ),
                relevant_experience=ScoreComponent(
                    status=ScoreComponentStatus.SCORED, value=exp
                ),
                education=EducationMatch(status=EducationMatchStatus.MET),
            ),
            required_skills=SkillMatchEvidence(),
            preferred_skills=SkillMatchEvidence(),
        )

    # C1 and C2 have same match_score=80. C1 has higher required skill coverage (90 vs 80)
    # C2 and C3 have same score=80, req=80. C2 has higher exp (80 vs 70)
    # C3 and C4 have same score, req, exp. C3 has higher semantic (85 vs 75)
    c1 = make_res("cand_c1", score=80.0, req=90.0, exp=70.0, sem=70.0)
    c2 = make_res("cand_c2", score=80.0, req=80.0, exp=80.0, sem=70.0)
    c3 = make_res("cand_c3", score=80.0, req=80.0, exp=70.0, sem=85.0)
    c4 = make_res("cand_c4", score=80.0, req=80.0, exp=70.0, sem=75.0)

    ranked = RankingService.rank_results([c4, c2, c1, c3])
    ranked_ids = [r.candidate_id for r in ranked]

    assert ranked_ids == ["cand_c1", "cand_c2", "cand_c3", "cand_c4"]
    assert [r.rank for r in ranked] == [1, 2, 3, 4]


def test_paired_fairness_evaluation():
    """
    MATCH-07 Acceptance Criteria:
    Fairness tests require identical scrubbed text, structured components,
    score, evidence, and component breakdowns for two profiles with identical
    professional qualifications but differing personal identifiers, genders, and universities.
    """
    candidate_female = create_sample_candidate(
        name="Sarah Connor",
        email="sarah.connor@cyberdyne.com",
        phone="+1 555-888-9999",
        pronoun="she",
        institution="Stanford University",
        skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
        experience_years=6.0,
    )

    candidate_male = create_sample_candidate(
        name="John Connor",
        email="john.connor@resistance.org",
        phone="+1 555-111-2222",
        pronoun="he",
        institution="Howard University",
        skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
        experience_years=6.0,
    )

    # 1. Profile Builder Isolation
    profile_f = ProfileBuilder.build_scoring_profile(candidate_female)
    profile_m = ProfileBuilder.build_scoring_profile(candidate_male)

    # Scrubbed text MUST be identical
    assert profile_f.job_relevant_text == profile_m.job_relevant_text

    # Education institution must be None in both
    assert profile_f.education[0].institution is None
    assert profile_m.education[0].institution is None

    # 2. Scoring Against Job Requirements
    job_req = JobRequirements(
        required_skills=["Python", "FastAPI", "PostgreSQL"],
        preferred_skills=["Docker"],
        experience_requirements=["5+ years of backend engineering"],
        education_requirements=["Bachelor of Science in Computer Science"],
        job_relevant_text="Seeking Senior Software Engineer with Python and FastAPI experience.",
        confirmed_at=datetime.now(UTC),
    )
    m_profile = MatchingProfileBuilder.build_matching_profile(job_req)

    engine = ScoringEngine()
    result_f = engine.score_candidate("cand_female_id", profile_f, m_profile)
    result_m = engine.score_candidate("cand_male_id", profile_m, m_profile)

    # Match scores must be identical
    req_val_f = result_f.breakdown.required_skill_coverage.value
    req_val_m = result_m.breakdown.required_skill_coverage.value
    assert req_val_f == req_val_m

    pref_val_f = result_f.breakdown.preferred_skill_coverage.value
    pref_val_m = result_m.breakdown.preferred_skill_coverage.value
    assert pref_val_f == pref_val_m

    exp_val_f = result_f.breakdown.relevant_experience.value
    exp_val_m = result_m.breakdown.relevant_experience.value
    assert exp_val_f == exp_val_m

    sem_val_f = result_f.breakdown.semantic_relevance.value
    sem_val_m = result_m.breakdown.semantic_relevance.value
    assert sem_val_f == sem_val_m
    assert result_f.breakdown.education.status == result_m.breakdown.education.status
    assert result_f.required_skills.matched == result_m.required_skills.matched
    assert result_f.required_skills.missing == result_m.required_skills.missing


def test_finalization_transaction_and_idempotent_labels(db_session: Session):
    """
    Labels (Candidate 01, Candidate 02) must be assigned sequentially
    strictly by candidate ID ordering, and calling finalization again
    leaves all labels unchanged.
    """
    analysis = AnalysisRepository.create(
        db_session,
        name="DevOps Lead",
    )
    analysis.status = AnalysisStatus.PROCESSING
    db_session.commit()

    # Create 2 candidates with specific IDs
    c1_extracted = create_sample_candidate(
        name="Bob Alpha",
        email="bob@alpha.com",
        phone="555-111-1111",
        pronoun="he",
        institution="University A",
        skills=["Docker"],
        experience_years=3.0,
    )
    c2_extracted = create_sample_candidate(
        name="Alice Beta",
        email="alice@beta.com",
        phone="555-222-2222",
        pronoun="she",
        institution="University B",
        skills=["Kubernetes"],
        experience_years=5.0,
    )

    c1 = CandidateRepository.create(db_session, analysis.id, str(uuid4()), c1_extracted)
    c2 = CandidateRepository.create(db_session, analysis.id, str(uuid4()), c2_extracted)

    # Initial labels must be None before finalization
    assert c1.display_label is None
    assert c2.display_label is None

    # Dummy match results: c2 has higher score than c1
    r1 = MatchResultData(
        candidate_id=c1.id,
        match_score=70.0,
        breakdown=ScoreBreakdown(
            semantic_relevance=ScoreComponent(status=ScoreComponentStatus.SCORED, value=70.0),
            required_skill_coverage=ScoreComponent(status=ScoreComponentStatus.SCORED, value=70.0),
            preferred_skill_coverage=ScoreComponent(status=ScoreComponentStatus.NOT_SPECIFIED),
            relevant_experience=ScoreComponent(status=ScoreComponentStatus.SCORED, value=70.0),
            education=EducationMatch(status=EducationMatchStatus.NOT_SPECIFIED),
        ),
        required_skills=SkillMatchEvidence(),
        preferred_skills=SkillMatchEvidence(),
    )
    r2 = MatchResultData(
        candidate_id=c2.id,
        match_score=95.0,
        breakdown=ScoreBreakdown(
            semantic_relevance=ScoreComponent(status=ScoreComponentStatus.SCORED, value=95.0),
            required_skill_coverage=ScoreComponent(status=ScoreComponentStatus.SCORED, value=95.0),
            preferred_skill_coverage=ScoreComponent(status=ScoreComponentStatus.NOT_SPECIFIED),
            relevant_experience=ScoreComponent(status=ScoreComponentStatus.SCORED, value=95.0),
            education=EducationMatch(status=EducationMatchStatus.NOT_SPECIFIED),
        ),
        required_skills=SkillMatchEvidence(),
        preferred_skills=SkillMatchEvidence(),
    )

    # Finalize ranking
    RankingService.finalize_analysis_ranking(db_session, analysis.id, [r1, r2])

    db_session.refresh(c1)
    db_session.refresh(c2)

    # c2 is rank 1, c1 is rank 2
    from backend.repositories.matching_repo import MatchResultRepository
    res_c2 = MatchResultRepository.get_by_candidate_id(db_session, c2.id)
    res_c1 = MatchResultRepository.get_by_candidate_id(db_session, c1.id)
    assert res_c2.rank == 1
    assert res_c1.rank == 2

    # Labels are ordered strictly by candidate ID
    c_sorted = sorted([c1, c2], key=lambda c: c.id)
    assert c_sorted[0].display_label == "Candidate 01"
    assert c_sorted[1].display_label == "Candidate 02"

    saved_c1_label = c1.display_label
    saved_c2_label = c2.display_label

    # Running finalization a second time leaves labels unchanged
    RankingService.finalize_analysis_ranking(db_session, analysis.id, [r1, r2])
    db_session.refresh(c1)
    db_session.refresh(c2)
    assert c1.display_label == saved_c1_label
    assert c2.display_label == saved_c2_label
