import re


class SkillExtractor:
    """
    Extracts and normalizes skills into canonical naming.
    Owned entirely by Person 1 as per ARCHITECTURE.md and RULES.md.
    """

    # Canonical Skill -> List of alias regex patterns
    CANONICAL_SKILL_MAP: dict[str, list[str]] = {
        "Python": [r"\bpython3?\b", r"\bpy\b"],
        "FastAPI": [r"\bfast[- ]?api\b"],
        "PostgreSQL": [r"\bpostgresql\b", r"\bpostgres\b", r"\bpsql\b"],
        "Docker": [r"\bdocker\b", r"\bdocker[- ]compose\b"],
        "AWS": [r"\baws\b", r"\bamazon web services\b"],
        "React": [r"\breact(?:\.js|js)?\b"],
        "JavaScript": [r"\bjavascript\b", r"\bjs\b", r"\becmascript\b"],
        "TypeScript": [r"\btypescript\b", r"\bts\b"],
        "Next.js": [r"\bnext(?:\.js|js)?\b"],
        "Tailwind CSS": [r"\btailwind(?:\s*css)?\b"],
        "CSS": [r"\bcss3?\b"],
        "HTML5": [r"\bhtml5?\b"],
        "Django": [r"\bdjango\b"],
        "Flask": [r"\bflask\b"],
        "Redis": [r"\bredis\b"],
        "SQLite": [r"\bsqlite3?\b"],
        "Git": [r"\bgit\b", r"\bgithub\b", r"\bgitlab\b"],
        "REST APIs": [r"\brest(?:ful)?\s*apis?\b", r"\brest\s*apis?\b"],
        "GraphQL": [r"\bgraphql\b"],
        "Kubernetes": [r"\bkubernetes\b", r"\bk8s\b"],
        "Linux": [r"\blinux\b", r"\bubuntu\b"],
        "SQL": [r"\bsql\b"],
        "Node.js": [r"\bnode(?:\.js|js)?\b"],
        "Java": [r"\bjava\b(?!\s*script)"],
        "C++": [r"\bc\+\+\b", r"\bcpp\b"],
        "Go": [r"\bgolang\b", r"\bgo\b(?!\s*to)"],
        "MongoDB": [r"\bmongodb\b", r"\bmongo\b"],
        "Microservices": [r"\bmicro[- ]?services?\b"],
    }

    @classmethod
    def extract_skills(cls, text: str) -> list[str]:
        """
        Scans text and returns an alphabetically sorted list of unique canonical skills.
        """
        if not text:
            return []

        matched_skills: set[str] = set()
        lower_text = text.lower()

        for canonical, patterns in cls.CANONICAL_SKILL_MAP.items():
            for pattern in patterns:
                if re.search(pattern, lower_text, re.IGNORECASE):
                    matched_skills.add(canonical)
                    break

        return sorted(list(matched_skills))

    @classmethod
    def normalize_skill(cls, skill_name: str) -> str:
        """
        Normalizes a single skill input string into its canonical equivalent.
        Returns the original skill if not matched in the canonical dictionary.
        """
        cleaned = skill_name.strip()
        lower = cleaned.lower()

        for canonical, patterns in cls.CANONICAL_SKILL_MAP.items():
            if lower == canonical.lower():
                return canonical
            for pattern in patterns:
                if re.fullmatch(pattern, lower, re.IGNORECASE):
                    return canonical

        return cleaned
