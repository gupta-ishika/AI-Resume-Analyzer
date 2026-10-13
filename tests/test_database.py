import pytest
from sqlalchemy.orm import Session

from backend.core.errors import ConflictError, ValidationError
from backend.repositories.analysis_repo import AnalysisRepository
from backend.repositories.candidate_repo import CandidateRepository
from backend.repositories.explanation_repo import ExplanationRepository
from backend.repositories.requirements_repo import JobRequirementsRepository
from backend.repositories.resume_repo import ResumeRepository
from backend.schemas.candidate import (
    CandidateExtractedData,
    CandidateIdentity,
)
from backend.schemas.common import (
    AnalysisStatus,
    ExplanationState,
    ResumeStatus,
)
from backend.schemas.requirements import JobRequirements, JobRequirementsUpdate
from backend.services.analysis_service import AnalysisService
from backend.services.upload_service import ResumeUploadService


def test_analysis_repository_lifecycle(db_session: Session):
    # 1. Create
    analysis = AnalysisRepository.create(db_session, name="Backend Engineer Role")
    assert analysis.id is not None
    assert analysis.status == AnalysisStatus.REQUIREMENTS_PENDING.value

    # 2. Get
    fetched = AnalysisRepository.get_by_id(db_session, analysis.id)
    assert fetched is not None
    assert fetched.name == "Backend Engineer Role"

    # 3. Conditional state transition
    success = AnalysisRepository.update_status_conditional(
        db_session,
        analysis.id,
        from_status=AnalysisStatus.REQUIREMENTS_PENDING.value,
        to_status=AnalysisStatus.PROCESSING.value,
    )
    assert success is True

    # 4. Repeated transition fails
    repeated = AnalysisRepository.update_status_conditional(
        db_session,
        analysis.id,
        from_status=AnalysisStatus.REQUIREMENTS_PENDING.value,
        to_status=AnalysisStatus.PROCESSING.value,
    )
    assert repeated is False

    # 5. Cannot delete while PROCESSING
    deleted = AnalysisRepository.mark_for_deletion(db_session, analysis.id)
    assert deleted is False

    # 6. Move to RANKED, then delete succeeds
    AnalysisRepository.update_status_conditional(
        db_session,
        analysis.id,
        from_status=AnalysisStatus.PROCESSING.value,
        to_status=AnalysisStatus.RANKED.value,
    )
    deleted = AnalysisRepository.mark_for_deletion(db_session, analysis.id)
    assert deleted is True

    # Hidden from get_by_id
    hidden = AnalysisRepository.get_by_id(db_session, analysis.id)
    assert hidden is None


def test_job_requirements_repository(db_session: Session):
    analysis = AnalysisRepository.create(db_session, name="Test Job")
    reqs = JobRequirements(
        required_skills=["Python", "FastAPI"],
        preferred_skills=["Docker"],
        experience_requirements=["3+ years"],
    )

    saved = JobRequirementsRepository.save_or_update(db_session, analysis.id, reqs)
    assert saved.analysis_id == analysis.id
    assert "Python" in saved.required_skills
    assert "Docker" in saved.preferred_skills

    # Update
    reqs.preferred_skills.append("AWS")
    updated = JobRequirementsRepository.save_or_update(db_session, analysis.id, reqs)
    assert "AWS" in updated.preferred_skills


def test_resume_upload_and_duplicate_detection(db_session: Session):
    analysis = AnalysisRepository.create(db_session, name="Resume Batch")
    dummy_pdf = b"%PDF-1.4 dummy resume content for applicant one"

    # 1. First upload -> READY
    res1 = ResumeUploadService.process_file_upload(
        db=db_session,
        analysis_id=analysis.id,
        filename="resume_1.pdf",
        file_bytes=dummy_pdf,
    )
    assert res1.status == ResumeStatus.READY.value
    assert res1.canonical_resume_id is None

    # 2. Duplicate upload of identical content -> DUPLICATE
    res2 = ResumeUploadService.process_file_upload(
        db=db_session,
        analysis_id=analysis.id,
        filename="resume_copy.pdf",
        file_bytes=dummy_pdf,
    )
    assert res2.status == ResumeStatus.DUPLICATE.value
    assert res2.canonical_resume_id == res1.id

    # 3. Unsupported format -> REJECTED
    res3 = ResumeUploadService.process_file_upload(
        db=db_session,
        analysis_id=analysis.id,
        filename="resume.txt",
        file_bytes=b"text file content",
    )
    assert res3.status == ResumeStatus.REJECTED.value
    assert res3.failure_reason_code == "UNSUPPORTED_FILE_TYPE"


def test_resume_claim_atomicity(db_session: Session):
    analysis = AnalysisRepository.create(db_session, name="Worker Claim Test")
    resume = ResumeRepository.register_resume(
        db=db_session,
        analysis_id=analysis.id,
        original_filename="cand.pdf",
        content_hash="abc123hash",
        temp_storage_key="test_key.pdf",
    )

    # First claim succeeds
    claimed = ResumeRepository.claim_resume(db_session, resume.id)
    assert claimed is True

    # Second claim fails (already claimed)
    claimed_again = ResumeRepository.claim_resume(db_session, resume.id)
    assert claimed_again is False


def test_accepted_resume_limit_enforcement(db_session: Session):
    analysis = AnalysisRepository.create(db_session, name="Limit Test")

    # Lower limit artificially for test speed
    original_limit = ResumeRepository.MAX_ACCEPTED_RESUMES
    ResumeRepository.MAX_ACCEPTED_RESUMES = 2
    try:
        r1 = ResumeRepository.register_resume(
            db=db_session,
            analysis_id=analysis.id,
            original_filename="c1.pdf",
            content_hash="hash_1",
        )
        assert r1.status == ResumeStatus.READY.value

        r2 = ResumeRepository.register_resume(
            db=db_session,
            analysis_id=analysis.id,
            original_filename="c2.pdf",
            content_hash="hash_2",
        )
        assert r2.status == ResumeStatus.READY.value

        # 3rd upload should be rejected with RESUME_LIMIT_EXCEEDED
        r3 = ResumeRepository.register_resume(
            db=db_session,
            analysis_id=analysis.id,
            original_filename="c3.pdf",
            content_hash="hash_3",
        )
        assert r3.status == ResumeStatus.REJECTED.value
        assert r3.failure_reason_code == "RESUME_LIMIT_EXCEEDED"
    finally:
        ResumeRepository.MAX_ACCEPTED_RESUMES = original_limit


def test_candidate_label_and_ranking_stability(db_session: Session):
    analysis = AnalysisRepository.create(db_session, name="Labeling Test")

    c1 = CandidateRepository.create(
        db_session,
        analysis.id,
        resume_id="res_01",
        data=CandidateExtractedData(
            identity=CandidateIdentity(name="Candidate Alpha"),
            skills=["Python"],
        ),
    )
    c2 = CandidateRepository.create(
        db_session,
        analysis.id,
        resume_id="res_02",
        data=CandidateExtractedData(
            identity=CandidateIdentity(name="Candidate Beta"),
            skills=["FastAPI"],
        ),
    )

    assert c1.display_label is None
    assert c2.display_label is None

    # Finalize ranking: c2 is rank 1, c1 is rank 2
    CandidateRepository.assign_labels_and_ranks(
        db=db_session,
        analysis_id=analysis.id,
        ranked_candidate_ids=[c2.id, c1.id],
    )

    db_session.refresh(c1)
    db_session.refresh(c2)

    # Labels are assigned sequentially by random candidate ID
    assert c1.display_label is not None
    assert c2.display_label is not None
    assert c1.display_label != c2.display_label

    label1 = c1.display_label
    label2 = c2.display_label

    # Running finalization a second time leaves existing labels unchanged
    CandidateRepository.assign_labels_and_ranks(
        db=db_session,
        analysis_id=analysis.id,
        ranked_candidate_ids=[c2.id, c1.id],
    )
    db_session.refresh(c1)
    db_session.refresh(c2)
    assert c1.display_label == label1
    assert c2.display_label == label2


def test_explanation_conditional_lifecycle(db_session: Session):
    analysis = AnalysisRepository.create(db_session, name="Expl Test")
    candidate = CandidateRepository.create(
        db_session,
        analysis.id,
        resume_id="res_expl",
        data=CandidateExtractedData(identity=CandidateIdentity(name="Candidate Expl")),
    )

    # 1. Start generation from NOT_REQUESTED -> True
    started = ExplanationRepository.start_generation_conditional(
        db_session, candidate.id, analysis.id
    )
    assert started is True

    # 2. Cannot start while already GENERATING -> False
    started_dup = ExplanationRepository.start_generation_conditional(
        db_session, candidate.id, analysis.id
    )
    assert started_dup is False

    # 3. Save explanation -> READY
    ExplanationRepository.save_explanation(
        db_session,
        candidate.id,
        content={"strengths": ["Strong background"], "gaps": []},
    )

    expl = ExplanationRepository.get_by_candidate_id(db_session, candidate.id)
    assert expl.state == ExplanationState.READY.value

    # 4. Cannot regenerate once READY -> False
    started_ready = ExplanationRepository.start_generation_conditional(
        db_session, candidate.id, analysis.id
    )
    assert started_ready is False

    # 5. Mark failed -> FAILED, then retry allowed -> True
    ExplanationRepository.mark_failed(db_session, candidate.id, "LLM timeout")
    retried = ExplanationRepository.start_generation_conditional(
        db_session, candidate.id, analysis.id
    )
    assert retried is True


def test_analysis_service_requirements_and_start_validation(db_session: Session):
    jd_text = "Looking for Senior Python Developer with FastAPI. 3+ years experience required."
    analysis, reqs = AnalysisService.create_analysis_from_jd(
        db=db_session,
        name="Python Backend Analysis",
        jd_text=jd_text,
    )
    assert "Python" in reqs.required_skills

    # Edit requirements
    AnalysisService.update_requirements(
        db=db_session,
        analysis_id=analysis.id,
        updates=JobRequirementsUpdate(
            required_skills=["Python", "FastAPI", "PostgreSQL"],
            preferred_skills=["Docker"],
            experience_requirements=["3+ years"],
            education_requirements=[],
            explicit_requirements=[],
        ),
    )

    # Confirm requirements
    confirmed = AnalysisService.confirm_requirements(db_session, analysis.id)
    assert confirmed.confirmed_at is not None

    # Cannot start without ready resume
    with pytest.raises(ValidationError):
        AnalysisService.validate_ready_for_start(db_session, analysis.id)

    # Add ready resume
    ResumeRepository.register_resume(
        db=db_session,
        analysis_id=analysis.id,
        original_filename="cand.pdf",
        content_hash="cand_hash_xyz",
    )

    # Now ready for start
    AnalysisService.validate_ready_for_start(db_session, analysis.id)

    # Move to PROCESSING
    AnalysisRepository.update_status_conditional(
        db_session,
        analysis.id,
        from_status=AnalysisStatus.REQUIREMENTS_PENDING.value,
        to_status=AnalysisStatus.PROCESSING.value,
    )

    # Requirement edits are now blocked
    with pytest.raises(ConflictError):
        AnalysisService.update_requirements(
            db=db_session,
            analysis_id=analysis.id,
            updates=JobRequirementsUpdate(
                required_skills=["Python"],
                preferred_skills=[],
                experience_requirements=[],
                education_requirements=[],
                explicit_requirements=[],
            ),
        )
