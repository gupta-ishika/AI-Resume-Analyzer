import io

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.repositories.analysis_repo import AnalysisRepository
from backend.repositories.candidate_repo import CandidateRepository
from backend.repositories.matching_repo import MatchResultRepository
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
    ExperienceEvidenceItem,
    MatchResultData,
    ScoreBreakdown,
    SkillMatchEvidence,
)


def test_create_and_manage_analysis_flow(client: TestClient):
    """
    API-02: Test POST /api/analyses, GET /api/analyses, PUT requirements, confirm requirements.
    """
    # 1. Create analysis with pasted text
    jd_payload = {
        "jd_text": (
            "Senior Python Engineer. Requirements: 5+ years of experience in Python and FastAPI. "
            "Bachelor's degree in Computer Science. Preferred: Docker."
        ),
        "name": "Python Lead Analysis",
    }
    create_resp = client.post("/api/analyses", data=jd_payload)
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    analysis_id = created_data["analysis"]["id"]
    assert created_data["analysis"]["name"] == "Python Lead Analysis"
    assert created_data["analysis"]["status"] == "REQUIREMENTS_PENDING"
    assert "Python" in created_data["requirements"]["required_skills"]

    # 2. Get analysis
    get_resp = client.get(f"/api/analyses/{analysis_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == analysis_id

    # 3. List analyses with pagination
    list_resp = client.get("/api/analyses?page=1&limit=10")
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1
    assert any(item["id"] == analysis_id for item in list_resp.json()["items"])

    # 4. Update requirements while in REQUIREMENTS_PENDING
    update_payload = {
        "required_skills": ["Python", "FastAPI", "PostgreSQL"],
        "preferred_skills": ["Docker", "Kubernetes"],
        "experience_requirements": ["5+ years of backend engineering"],
        "education_requirements": ["Bachelor's degree in Computer Science"],
        "explicit_requirements": ["Strong problem-solving skills"],
    }
    update_resp = client.put(f"/api/analyses/{analysis_id}/requirements", json=update_payload)
    assert update_resp.status_code == 200
    assert "PostgreSQL" in update_resp.json()["required_skills"]

    # 5. Confirm requirements
    confirm_resp = client.post(f"/api/analyses/{analysis_id}/requirements/confirm")
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["confirmed_at"] is not None


def test_create_analysis_with_file_upload(client: TestClient):
    """API-02: Test POST /api/analyses with uploaded file."""
    file_content = (
        b"Machine Learning Engineer\n"
        b"Requirements: Python, PyTorch, Scikit-Learn\n"
        b"Experience: 3+ years in AI\n"
    )
    files = {
        "jd_file": (
            "job_description.docx",
            file_content,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }
    resp = client.post("/api/analyses", files=files, data={"name": "ML Engineer"})
    # Dummy docx bytes are not a valid zip archive; categorized as unreadable
    assert resp.status_code == 400
    err = resp.json()["error"]
    assert err["code"] == "DOCUMENT_UNREADABLE"


def test_resume_upload_and_list_flow(client: TestClient):
    """
    API-03: Test POST /api/analyses/{id}/resumes and GET /api/analyses/{id}/resumes.
    """
    # Create analysis
    analysis_resp = client.post(
        "/api/analyses",
        data={"jd_text": "Software Engineer with Python skills", "name": "Resume Upload Test"},
    )
    analysis_id = analysis_resp.json()["analysis"]["id"]

    # 1. Upload valid resume (PDF supported in loader/upload service)
    cv1_content = (
        b"%PDF-1.4\nAlice Smith\nalice@example.com\n\n"
        b"Technical Skills\nPython, Docker\n\n"
        b"Professional Experience\nBackend Developer, 3 years\n"
    )
    files = [("files", ("alice_cv.pdf", io.BytesIO(cv1_content), "application/pdf"))]
    upload_resp = client.post(f"/api/analyses/{analysis_id}/resumes", files=files)
    assert upload_resp.status_code == 200
    upload_data = upload_resp.json()
    assert upload_data["accepted_count"] == 1
    assert upload_data["results"][0]["status"] == "READY"

    # 2. Upload duplicate content
    files_dup = [
        ("files", ("alice_cv_copy.pdf", io.BytesIO(cv1_content), "application/pdf"))
    ]
    dup_resp = client.post(f"/api/analyses/{analysis_id}/resumes", files=files_dup)
    assert dup_resp.status_code == 200
    assert dup_resp.json()["results"][0]["status"] == "DUPLICATE"

    # 3. List resumes
    list_resumes_resp = client.get(f"/api/analyses/{analysis_id}/resumes")
    assert list_resumes_resp.status_code == 200
    items = list_resumes_resp.json()["items"]
    assert len(items) == 2
    assert any(r["status"] == "READY" for r in items)
    assert any(r["status"] == "DUPLICATE" for r in items)


def test_start_and_status_endpoints(client: TestClient, db_session: Session):
    """API-04: Test start analysis and polling status endpoint."""
    analysis = AnalysisRepository.create(db_session, name="Start Status API Test")
    from datetime import UTC, datetime

    from backend.repositories.requirements_repo import JobRequirementsRepository
    from backend.schemas.requirements import JobRequirements
    job_req = JobRequirements(
        required_skills=["Python"],
        confirmed_at=datetime.now(UTC),
    )
    JobRequirementsRepository.save_or_update(db_session, analysis.id, job_req)

    # Register 1 READY resume
    from backend.repositories.resume_repo import ResumeRepository
    from tests.test_background import create_temp_resume_file
    storage_key, chash = create_temp_resume_file(
        "John Doe\njohn@test.com\nSkills: Python\nExperience: 4 years\n"
    )
    ResumeRepository.register_resume(
        db=db_session,
        analysis_id=analysis.id,
        original_filename="john.txt",
        content_hash=chash,
        temp_storage_key=storage_key,
    )

    # Call POST /api/analyses/{id}/start
    start_resp = client.post(f"/api/analyses/{analysis.id}/start")
    assert start_resp.status_code == 200
    assert start_resp.json()["status"] == "PROCESSING"

    # Call GET /api/analyses/{id}/status
    status_resp = client.get(f"/api/analyses/{analysis.id}/status")
    assert status_resp.status_code == 200
    s_data = status_resp.json()
    assert s_data["total"] == 1
    assert s_data["processed"] == 1
    assert s_data["successful"] == 1


def test_candidate_list_and_detail_endpoints(client: TestClient, db_session: Session):
    """
    API-05: Test GET /api/analyses/{id}/candidates and candidate detail.
    Enforces that candidate list does not expose names/contact info.
    """
    analysis = AnalysisRepository.create(db_session, name="Candidate API Test")
    analysis.status = AnalysisStatus.RANKED.value
    db_session.commit()

    # Add a candidate with match result
    extracted = CandidateExtractedData(
        identity=CandidateIdentity(
            name="Secret Name",
            contact=CandidateContact(email="secret@email.com", phone="123-456"),
        ),
        skills=["Python", "FastAPI"],
        experience=[
            ExperienceItem(
                title="Lead Dev",
                company=None,
                duration="5 years",
                years=5.0,
                responsibilities=["Built cloud services"],
            )
        ],
        projects=[
            ProjectItem(
                name="API Service",
                description="FastAPI app",
                technologies=["FastAPI"],
            )
        ],
        education=[EducationItem(degree="Bachelor of Science", field_of_study="CS")],
    )
    cand = CandidateRepository.create(db_session, analysis.id, "resume_123", extracted)
    cand.display_label = "Candidate 01"
    db_session.commit()

    match_res = MatchResultData(
        candidate_id=cand.id,
        match_score=92.5,
        rank=1,
        breakdown=ScoreBreakdown(
            semantic_relevance=ScoreComponent(status=ScoreComponentStatus.SCORED, value=90.0),
            required_skill_coverage=ScoreComponent(status=ScoreComponentStatus.SCORED, value=100.0),
            preferred_skill_coverage=ScoreComponent(status=ScoreComponentStatus.NOT_SPECIFIED),
            relevant_experience=ScoreComponent(status=ScoreComponentStatus.SCORED, value=90.0),
            education=EducationMatch(status=EducationMatchStatus.MET),
        ),
        required_skills=SkillMatchEvidence(matched=["Python", "FastAPI"]),
        preferred_skills=SkillMatchEvidence(),
        experience_evidence=[ExperienceEvidenceItem(summary="Lead Dev (5.0 years)")],
    )
    MatchResultRepository.save_or_update(db_session, analysis.id, match_res)

    # 1. GET /api/analyses/{id}/candidates
    list_cand_resp = client.get(f"/api/analyses/{analysis.id}/candidates")
    assert list_cand_resp.status_code == 200
    ranking = list_cand_resp.json()["ranking"]
    assert len(ranking) == 1
    assert ranking[0]["label"] == "Candidate 01"
    assert ranking[0]["match_score"] == 92.5
    # Verification: identity fields MUST NOT be present in candidate list!
    assert "name" not in ranking[0]
    assert "email" not in ranking[0]

    # 2. GET /api/analyses/{id}/candidates/{cand_id}
    detail_resp = client.get(f"/api/analyses/{analysis.id}/candidates/{cand.id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["candidate_id"] == cand.id
    assert detail["label"] == "Candidate 01"
    assert detail["identity"]["name"] == "Secret Name"
    assert detail["identity"]["contact"]["email"] == "secret@email.com"
    assert detail["matching"]["match_score"] == 92.5
    assert detail["explanation"]["state"] == "NOT_REQUESTED"


def test_delete_analysis_endpoint(client: TestClient, db_session: Session):
    """
    API-06: Test DELETE /api/analyses/{id}.
    - Processing analysis returns 409
    - Success returns 202
    - Repeated delete returns 404
    """
    # 1. Reject delete while PROCESSING
    analysis = AnalysisRepository.create(db_session, name="Delete In Progress Test")
    analysis.status = AnalysisStatus.PROCESSING.value
    db_session.commit()

    del_processing_resp = client.delete(f"/api/analyses/{analysis.id}")
    assert del_processing_resp.status_code == 409
    assert del_processing_resp.json()["error"]["code"] == "ANALYSIS_PROCESSING"

    # 2. Allow delete when REQUIREMENTS_PENDING or RANKED
    analysis.status = AnalysisStatus.RANKED.value
    db_session.commit()

    del_success_resp = client.delete(f"/api/analyses/{analysis.id}")
    assert del_success_resp.status_code == 202

    # 3. Repeated delete returns 404
    del_repeated_resp = client.delete(f"/api/analyses/{analysis.id}")
    assert del_repeated_resp.status_code == 404
    assert del_repeated_resp.json()["error"]["code"] == "ANALYSIS_NOT_FOUND"
