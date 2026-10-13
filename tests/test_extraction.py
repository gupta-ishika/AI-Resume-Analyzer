import json
from pathlib import Path

from backend.schemas.extraction import ExtractionFailureCode, ExtractionStatus
from backend.services.document_loader import DocumentLoaderService
from backend.services.jd_extractor import JDExtractor
from backend.services.profile_extractor import ProfileExtractor
from backend.services.section_detector import SectionDetector
from backend.services.skill_extractor import SkillExtractor
from backend.services.text_cleaner import TextCleaner


def test_document_loader_unsupported_format():
    result = DocumentLoaderService.extract_text_from_bytes(b"some content", "resume.xyz")
    assert result.status == ExtractionStatus.FAILED
    assert result.failure_code == ExtractionFailureCode.UNSUPPORTED_FORMAT


def test_document_loader_empty_document():
    result = DocumentLoaderService.extract_text_from_bytes(b"   ", "resume.pdf")
    assert result.status == ExtractionStatus.FAILED
    assert result.failure_code == ExtractionFailureCode.EMPTY_DOCUMENT


def test_text_cleaner():
    raw = "John   Doe \t\n\n\n\nSkills:\r\nPython \u00a0 and  FastAPI\n"
    cleaned = TextCleaner.clean(raw)
    assert "John Doe" in cleaned
    assert "Python and FastAPI" in cleaned
    assert "\n\n\n" not in cleaned


def test_skill_normalization_and_synonyms():
    text = "Proficient in JS, Postgres, react.js, and python3. Also knows Docker."
    skills = SkillExtractor.extract_skills(text)
    assert "JavaScript" in skills
    assert "PostgreSQL" in skills
    assert "React" in skills
    assert "Python" in skills
    assert "Docker" in skills


def test_skill_boundary_matching():
    text = "We use Java for backend services."
    skills = SkillExtractor.extract_skills(text)
    assert "Java" in skills
    assert "JavaScript" not in skills


def test_section_detector():
    text = """ALEX MORGAN
Email: alex@example.com

SKILLS
Python, FastAPI, PostgreSQL

PROFESSIONAL EXPERIENCE
Senior Engineer at Acme Corp
- Built REST APIs

EDUCATION
Bachelor of Science in Computer Science
"""
    sections = SectionDetector.detect_sections(text)
    assert "header" in sections
    assert "skills" in sections
    assert "experience" in sections
    assert "education" in sections


def test_profile_extractor():
    text = """JANE DOE
Email: jane.doe@example.com | Phone: (555) 123-4567

TECHNICAL SKILLS
Python, PostgreSQL, Docker

EXPERIENCE
Software Engineer (2020 - 2023, 3 years)
- Developed backend microservices using Python and PostgreSQL.

EDUCATION
Bachelor's Degree in Software Engineering, State University
"""
    candidate = ProfileExtractor.extract_candidate(text)
    assert candidate.identity.name == "JANE DOE"
    assert candidate.identity.contact.email == "jane.doe@example.com"
    assert candidate.identity.contact.phone == "(555) 123-4567"
    assert "Python" in candidate.skills
    assert "PostgreSQL" in candidate.skills
    assert len(candidate.experience) >= 1
    assert candidate.experience[0].years == 3.0
    assert len(candidate.education) >= 1
    assert "Bachelor" in candidate.education[0].degree


def test_jd_extractor_required_vs_preferred():
    jd_text = """We need a Senior Backend Developer with expertise in Python and FastAPI.
Must have at least 3+ years of experience. Bachelor's degree required.
Experience with Docker and AWS is preferred and a nice to have."""

    reqs = JDExtractor.extract_requirements(jd_text)
    assert "Python" in reqs.required_skills
    assert "FastAPI" in reqs.required_skills
    assert "Docker" in reqs.preferred_skills
    assert "AWS" in reqs.preferred_skills


def test_seed_dataset_benchmark():
    seed_file = Path("data/seed/resumes.json")
    assert seed_file.exists(), "Seed dataset resumes.json must exist"

    with open(seed_file, encoding="utf-8") as f:
        resumes = json.load(f)

    for item in resumes:
        if item.get("expected_status") == "SUCCESS":
            extracted = ProfileExtractor.extract_candidate(item["text"])
            for skill in item.get("expected_skills", []):
                assert skill in extracted.skills, (
                    f"Candidate {item['id']} missing expected skill {skill}"
                )
