import re

from backend.schemas.requirements import JobRequirements
from backend.services.skill_extractor import SkillExtractor
from backend.services.text_cleaner import TextCleaner


class JDExtractor:
    """Extracts structured requirements from Job Description text."""

    PREFERRED_KEYWORDS = [
        r"\b(?:preferred|nice[- ]to[- ]have|bonus|plus|desirable|optional)\b",
    ]

    EXPERIENCE_PATTERN = (
        r"(?:(?:at least|\bmin(?:imum)?\b)?\s*(\d+(?:\.\d+)?)\s*\+?\s*years?"
        r"(?:\s+of)?(?:\s+experience)?(?:[^\n.]+)?)"
    )
    EDUCATION_PATTERN = (
        r"(?:bachelor(?:'s)?|master(?:'s)?|ph\.?d|b\.?s\.?|b\.?tech|associate(?:'s)?)"
        r"(?:[^\n.]+)"
    )

    @classmethod
    def extract_requirements(cls, jd_text: str) -> JobRequirements:
        cleaned_text = TextCleaner.clean(jd_text)
        if not cleaned_text:
            return JobRequirements()

        # Segment sentences or lines into required vs preferred
        preferred_skills: set[str] = set()
        required_skills: set[str] = set()

        sentences = re.split(r"(?<=[.!?])\s+|\n+", cleaned_text)
        for sentence in sentences:
            s_skills = SkillExtractor.extract_skills(sentence)
            if not s_skills:
                continue

            is_preferred = any(
                re.search(pat, sentence, re.IGNORECASE) for pat in cls.PREFERRED_KEYWORDS
            )
            if is_preferred:
                preferred_skills.update(s_skills)
            else:
                required_skills.update(s_skills)

        # Preferred skills should not collide with required skills
        # If a skill appears in both, required takes precedence
        preferred_skills = preferred_skills - required_skills

        # If everything fell into preferred, promote to required
        if not required_skills and preferred_skills:
            required_skills = preferred_skills
            preferred_skills = set()

        # Extract experience requirements
        exp_matches = re.findall(cls.EXPERIENCE_PATTERN, cleaned_text, re.IGNORECASE)
        experience_requirements = [m.strip() for m in exp_matches if len(m.strip()) > 5][:5]

        # Extract education requirements
        edu_matches = re.findall(cls.EDUCATION_PATTERN, cleaned_text, re.IGNORECASE)
        education_requirements = [m.strip() for m in edu_matches if len(m.strip()) > 5][:3]

        return JobRequirements(
            required_skills=sorted(list(required_skills)),
            preferred_skills=sorted(list(preferred_skills)),
            experience_requirements=experience_requirements,
            education_requirements=education_requirements,
            explicit_requirements=[],
            job_relevant_text=cleaned_text,
        )
