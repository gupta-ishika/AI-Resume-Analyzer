import re

from backend.schemas.requirements import JobRequirements
from backend.services.skill_extractor import SkillExtractor
from backend.services.text_cleaner import TextCleaner


class JDExtractor:
    """Extracts structured requirements from Job Description text."""

    PREFERRED_KEYWORDS = [
        r"\b(?:preferred|nice[- ]to[- ]have|bonus|plus|desirable|optional)\b",
    ]
    REQUIRED_KEYWORDS = [
        r"\b(?:required|mandatory|must[- ]have|core required|minimum qualifications|qualifications|requirements)\b",
    ]
    RESPONSIBILITIES_KEYWORDS = [
        r"\b(?:responsibilities|duties|what you (?:will )?do|what you\'ll do|day[- ]to[- ]day|about the (?:role|team|opportunity|mission)|role overview)\b"
    ]

    EXPERIENCE_PATTERN = (
        r"((?:(?:at least|\bmin(?:imum)?\b)?\s*\d+(?:\.\d+)?\s*\+?\s*years?"
        r"(?:\s+of)?(?:\s+[\w\s-]+)?experience)[^.:;\n]*)"
    )
    FALLBACK_EXP = r"(\b\d+(?:\.\d+)?\s*\+?\s*years?(?:\s+exp\b)?[^.:;\n]*)"

    EDUCATION_PATTERN = (
        r"(\b(?:bachelor(?:[\'’]s)?(?:\s+of\s+[\w\s]+)?|master(?:[\'’]s)?(?:\s+of\s+[\w\s]+)?|ph\.?d\.?|b\.s\.?|m\.s\.?|b\.?tech|associate(?:[\'’]s)?)"
        r"(?:\s+or\s+(?:master(?:[\'’]s)?|m\.s\.?|ph\.?d\.?))?"
        r"(?:\s+degree)?(?:\s+in\s+[\w\s/,-]+)?)"
    )

    @classmethod
    def clean_criterion(cls, s: str) -> str:
        """Strips boundary punctuation and balances stray parentheses."""
        res = s.strip(" \t\r\n.,;:) ")
        while res.count("(") < res.count(")"):
            res = res.rstrip(")")
        while res.count("(") > res.count(")"):
            res = res.lstrip("(")
        return res.strip()

    @classmethod
    def extract_requirements(cls, jd_text: str) -> JobRequirements:
        cleaned_text = TextCleaner.clean(jd_text)
        if not cleaned_text:
            return JobRequirements()

        # Unwrap soft line wraps inside paragraphs for clean experience/education capture
        unwrapped_text = re.sub(r"(?<![\n.:;•\-])\n(?!\s*[-•*\d]+\.|\s*#|\s*$)", " ", cleaned_text)

        lines = [line.strip() for line in cleaned_text.split("\n") if line.strip()]
        preferred_skills: set[str] = set()
        required_skills: set[str] = set()
        general_skills: set[str] = set()

        current_section = "intro"

        for line in lines:
            is_pref_heading = any(re.search(pat, line, re.IGNORECASE) for pat in cls.PREFERRED_KEYWORDS)
            is_req_heading = any(re.search(pat, line, re.IGNORECASE) for pat in cls.REQUIRED_KEYWORDS)
            is_resp_heading = any(re.search(pat, line, re.IGNORECASE) for pat in cls.RESPONSIBILITIES_KEYWORDS)

            if is_pref_heading:
                current_section = "preferred"
            elif is_req_heading:
                current_section = "required"
            elif is_resp_heading:
                current_section = "responsibilities"

            s_skills = SkillExtractor.extract_skills(line)
            if not s_skills:
                continue

            if is_pref_heading or (current_section == "preferred"):
                preferred_skills.update(s_skills)
            elif is_req_heading or (current_section == "required"):
                required_skills.update(s_skills)
            else:
                general_skills.update(s_skills)

        # Explicit preferred skills take precedence over general overview mentions
        preferred_skills = preferred_skills - required_skills

        # Augment required skills with any intro/responsibility skills that weren't marked preferred
        for s in general_skills:
            if s not in preferred_skills:
                required_skills.add(s)

        # If everything fell into preferred, promote to required
        if not required_skills and preferred_skills:
            required_skills = preferred_skills
            preferred_skills = set()

        # Extract experience requirements
        exp_matches = re.findall(cls.EXPERIENCE_PATTERN, unwrapped_text, re.IGNORECASE)
        experience_requirements = [
            cls.clean_criterion(m) for m in exp_matches if len(cls.clean_criterion(m)) > 5
        ][:5]
        if not experience_requirements:
            f_matches = re.findall(cls.FALLBACK_EXP, unwrapped_text, re.IGNORECASE)
            experience_requirements = [
                cls.clean_criterion(m) for m in f_matches if len(cls.clean_criterion(m)) >= 3
            ][:5]

        # Extract education requirements
        edu_matches = [m.group(0) for m in re.finditer(cls.EDUCATION_PATTERN, unwrapped_text, re.IGNORECASE)]
        education_requirements = [
            cls.clean_criterion(m) for m in edu_matches if len(cls.clean_criterion(m)) > 3
        ][:3]

        return JobRequirements(
            required_skills=sorted(list(required_skills)),
            preferred_skills=sorted(list(preferred_skills)),
            experience_requirements=experience_requirements,
            education_requirements=education_requirements,
            explicit_requirements=[],
            job_relevant_text=cleaned_text,
        )
