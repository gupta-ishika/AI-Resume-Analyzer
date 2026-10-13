import re


class SectionDetector:
    """Splits a cleaned resume text into recognized functional sections."""

    SECTION_PATTERNS = {
        "skills": [
            r"^(?:technical\s+)?skills",
            r"^core\s+competencies",
            r"^technologies",
            r"^technical\s+expertise",
            r"^tools\s+(&|and)\s+technologies",
        ],
        "experience": [
            r"^(?:professional\s+|work\s+)?experience",
            r"^employment\s+history",
            r"^work\s+history",
            r"^career\s+history",
        ],
        "projects": [
            r"^(?:key\s+|featured\s+|personal\s+)?projects",
            r"^project\s+experience",
        ],
        "education": [
            r"^education(?:al\s+background)?",
            r"^academic\s+(?:background|history|credentials)",
            r"^degrees",
        ],
        "summary": [
            r"^(?:professional\s+)?summary",
            r"^profile",
            r"^about\s+me",
            r"^objective",
        ],
    }

    @classmethod
    def detect_sections(cls, text: str) -> dict[str, str]:
        """
        Parses text and returns a dictionary of section_name -> section_content.
        Uncategorized header text (e.g. name/contact) is stored under 'header'.
        """
        if not text:
            return {}

        lines = text.split("\n")
        sections: dict[str, list[str]] = {"header": []}
        current_section = "header"

        for line in lines:
            trimmed = line.strip()
            if not trimmed:
                if current_section in sections:
                    sections[current_section].append("")
                continue

            # Check if this line looks like a section header
            matched_section = cls._match_header(trimmed)
            if matched_section:
                current_section = matched_section
                if current_section not in sections:
                    sections[current_section] = []
            else:
                sections[current_section].append(trimmed)

        # Convert line lists to clean joined strings
        return {
            sec: "\n".join(content_lines).strip()
            for sec, content_lines in sections.items()
            if any(c_line.strip() for c_line in content_lines)
        }

    @classmethod
    def _match_header(cls, line: str) -> str | None:
        # Check if line is short enough to be a heading (typically < 45 chars)
        cleaned = re.sub(r"[:#\-_]+$", "", line).strip()
        if len(cleaned) > 45:
            return None

        clean_lower = cleaned.lower()
        for section_name, patterns in cls.SECTION_PATTERNS.items():
            for pat in patterns:
                if re.match(pat, clean_lower, re.IGNORECASE):
                    return section_name
        return None
