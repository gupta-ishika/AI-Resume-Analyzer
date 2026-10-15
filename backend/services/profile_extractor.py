import re

from backend.schemas.candidate import (
    CandidateContact,
    CandidateExtractedData,
    CandidateIdentity,
    EducationItem,
    ExperienceItem,
    ProjectItem,
)
from backend.services.section_detector import SectionDetector
from backend.services.skill_extractor import SkillExtractor
from backend.services.text_cleaner import TextCleaner


class ProfileExtractor:
    """Extracts structured information from resume text into CandidateExtractedData."""

    EMAIL_REGEX = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
    PHONE_REGEX = r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"

    YEARS_EXP_REGEX = r"(\d+(?:\.\d+)?)\s*\+?\s*years?"

    @classmethod
    def extract_candidate(cls, raw_text: str) -> CandidateExtractedData:
        cleaned_text = TextCleaner.clean(raw_text)
        sections = SectionDetector.detect_sections(cleaned_text)

        identity = cls._extract_identity(cleaned_text, sections.get("header", ""))
        skills = SkillExtractor.extract_skills(cleaned_text)
        experience = cls._extract_experience(sections.get("experience", ""))
        education = cls._extract_education(sections.get("education", ""), cleaned_text)
        projects = cls._extract_projects(sections.get("projects", ""))

        return CandidateExtractedData(
            identity=identity,
            skills=skills,
            experience=experience,
            projects=projects,
            education=education,
        )

    @classmethod
    def _extract_identity(cls, full_text: str, header_text: str) -> CandidateIdentity:
        # Extract email
        email_match = re.search(cls.EMAIL_REGEX, full_text)
        email = email_match.group(0) if email_match else None

        # Extract phone
        phone_match = re.search(cls.PHONE_REGEX, full_text)
        phone = phone_match.group(0) if phone_match else None

        # Extract name: usually the first non-empty line of the header or document
        name = "Unknown Candidate"
        lines = [line.strip() for line in (header_text or full_text).split("\n") if line.strip()]
        for line in lines:
            # Skip lines that look like emails, URLs, or labels
            if "@" in line or "http" in line or ":" in line:
                continue
            if len(line.split()) <= 4 and any(c.isalpha() for c in line):
                name = line
                break

        return CandidateIdentity(
            name=name,
            contact=CandidateContact(email=email, phone=phone),
        )

    DATE_RANGE_REGEX = (
        r"\(?(\b(?:19|20)\d{2}\b\s*(?:-|–|to)\s*(?:\b(?:19|20)\d{2}\b|present|current|now))\)?"
    )

    @classmethod
    def _extract_experience(cls, exp_text: str) -> list[ExperienceItem]:
        if not exp_text:
            return []

        lines = [line.strip() for line in exp_text.split("\n") if line.strip()]
        items: list[ExperienceItem] = []
        curr_job: ExperienceItem | None = None
        current_year = 2026

        for line in lines:
            d_match = re.search(cls.DATE_RANGE_REGEX, line, re.IGNORECASE)
            is_bullet = line.startswith(("-", "•", "*", "\x7f"))
            is_header = bool(d_match) or (not is_bullet and ("|" in line))

            if is_header:
                if curr_job:
                    items.append(curr_job)

                duration = d_match.group(1) if d_match else None
                years = 0.0
                if d_match:
                    parts = re.findall(
                        r"\b(?:19|20)\d{2}\b|present|current|now", d_match.group(1), re.IGNORECASE
                    )
                    if len(parts) >= 2:
                        s_yr = int(parts[0])
                        e_yr = current_year if parts[1].lower() in ("present", "current", "now") else int(parts[1])
                        years = max(0.5, float(e_yr - s_yr))
                else:
                    y_match = re.search(cls.YEARS_EXP_REGEX, line, re.IGNORECASE)
                    if y_match:
                        try:
                            years = float(y_match.group(1))
                        except ValueError:
                            years = 0.0

                clean_title = re.sub(cls.DATE_RANGE_REGEX, "", line).strip(" ()|")
                company = None
                if "|" in clean_title:
                    parts = clean_title.split("|", 1)
                    clean_title = parts[0].strip()
                    company = re.sub(cls.DATE_RANGE_REGEX, "", parts[1]).strip(" ()|")

                curr_job = ExperienceItem(
                    title=clean_title[:100],
                    company=company[:100] if company else None,
                    duration=duration,
                    years=years,
                    responsibilities=[],
                )
            elif curr_job:
                clean_resp = line.lstrip("-•*\x7f ").strip()
                if len(clean_resp) > 10:
                    curr_job.responsibilities.append(clean_resp)

        if curr_job:
            items.append(curr_job)

        # Fallback to block splitting if line scanning did not identify items
        if not items:
            blocks = [b.strip() for b in exp_text.split("\n\n") if b.strip()]
            for block in blocks:
                b_lines = [l.strip() for l in block.split("\n") if l.strip()]
                if not b_lines:
                    continue
                years = 0.0
                y_match = re.search(cls.YEARS_EXP_REGEX, block, re.IGNORECASE)
                if y_match:
                    try:
                        years = float(y_match.group(1))
                    except ValueError:
                        years = 0.0
                items.append(
                    ExperienceItem(
                        title=b_lines[0][:100],
                        company=None,
                        duration=None,
                        years=years,
                        responsibilities=[
                            l.lstrip("-•* ").strip()
                            for l in b_lines[1:]
                            if l.startswith(("-", "•", "*")) or len(l) > 20
                        ],
                    )
                )

        return items

    @classmethod
    def _extract_education(cls, edu_text: str, full_text: str) -> list[EducationItem]:
        search_target = edu_text if edu_text else full_text
        items: list[EducationItem] = []

        degrees = [
            (r"\b(?:bachelor(?:'s)?|b\.?s\.?|b\.?tech|b\.?e\.?|b\.?a\.?)\b", "Bachelor's Degree"),
            (r"\b(?:master(?:'s)?|m\.?s\.?|m\.?tech|m\.?b\.?a\.?)\b", "Master's Degree"),
            (r"\b(?:ph\.?d\.?|doctorate)\b", "Doctorate / Ph.D"),
            (r"\b(?:associate(?:'s)?)\b", "Associate Degree"),
        ]

        for pattern, degree_name in degrees:
            match = re.search(pattern, search_target, re.IGNORECASE)
            if match:
                # Find line containing the degree
                inst_name = None
                for line in search_target.split("\n"):
                    if re.search(pattern, line, re.IGNORECASE):
                        # Simple institution heuristic (e.g. University, Institute, College)
                        inst_match = re.search(
                            r"(?:at\s+|,\s+)?([A-Za-z\s]+(?:University|College|Institute|School))",
                            line,
                            re.IGNORECASE,
                        )
                        if inst_match:
                            inst_name = inst_match.group(1).strip()
                        break

                items.append(
                    EducationItem(
                        degree=degree_name,
                        field_of_study=None,
                        institution=inst_name,
                    )
                )

        return items

    @classmethod
    def _extract_projects(cls, proj_text: str) -> list[ProjectItem]:
        if not proj_text:
            return []

        items: list[ProjectItem] = []
        blocks = [b.strip() for b in proj_text.split("\n\n") if b.strip()]

        for block in blocks:
            lines = [line.strip() for line in block.split("\n") if line.strip()]
            if not lines:
                continue

            name = lines[0].split(":")[0].strip()
            desc = " ".join(lines)
            techs = SkillExtractor.extract_skills(desc)

            items.append(
                ProjectItem(
                    name=name[:100],
                    description=desc,
                    technologies=techs,
                )
            )

        return items

    extract_profile = extract_candidate

