import json
import os
import re
from pathlib import Path
from flashtext import KeywordProcessor


class SkillExtractor:
    """
    Extracts and normalizes skills into canonical naming using FlashText
    backed by a structured offline taxonomy (backend/data/skills_taxonomy.json).
    """

    TAXONOMY_PATH = Path(__file__).resolve().parent.parent / "data" / "skills_taxonomy.json"

    SKILL_IMPLICATIONS: dict[str, list[str]] = {
        "PostgreSQL": ["SQL"],
        "SQLite": ["SQL"],
        "MySQL": ["SQL"],
    }

    _processor: KeywordProcessor | None = None
    _short_word_processor: KeywordProcessor | None = None
    _alias_map: dict[str, str] = {}

    @classmethod
    def _initialize(cls) -> None:
        if cls._processor is not None:
            return

        cls._processor = KeywordProcessor(case_sensitive=False)
        cls._short_word_processor = KeywordProcessor(case_sensitive=True)

        # Allow non-word boundaries for tech terms containing symbols
        cls._processor.add_non_word_boundary("+")
        cls._processor.add_non_word_boundary("#")
        cls._short_word_processor.add_non_word_boundary("+")
        cls._short_word_processor.add_non_word_boundary("#")

        if cls.TAXONOMY_PATH.exists():
            with open(cls.TAXONOMY_PATH, "r", encoding="utf-8") as f:
                taxonomy: dict[str, list[str]] = json.load(f)
        else:
            taxonomy = {}

        cls._alias_map = {}

        # Terms with <=2 characters that require case-sensitive matching to avoid false positives
        case_sensitive_terms = {"Go", "C", "R"}

        for canonical, aliases in taxonomy.items():
            cls._alias_map[canonical.lower()] = canonical

            if canonical in case_sensitive_terms:
                cls._short_word_processor.add_keyword(canonical, canonical)
            else:
                cls._processor.add_keyword(canonical, canonical)

            for alias in aliases:
                cls._alias_map[alias.lower()] = canonical
                if alias in case_sensitive_terms:
                    cls._short_word_processor.add_keyword(alias, canonical)
                else:
                    cls._processor.add_keyword(alias, canonical)

    @classmethod
    def extract_skills(cls, text: str) -> list[str]:
        """
        Scans text and returns an alphabetically sorted list of unique canonical skills.
        """
        if not text:
            return []

        cls._initialize()
        assert cls._processor is not None
        assert cls._short_word_processor is not None

        matched_skills: set[str] = set()

        # 1. Standard dictionary-based match (case-insensitive)
        standard_matches = cls._processor.extract_keywords(text)
        matched_skills.update(standard_matches)

        # 2. Guarded short-word match (case-sensitive)
        short_matches = cls._short_word_processor.extract_keywords(text)
        matched_skills.update(short_matches)

        # 3. Relational database dialects naturally imply general SQL competence
        for skill in list(matched_skills):
            if skill in cls.SKILL_IMPLICATIONS:
                matched_skills.update(cls.SKILL_IMPLICATIONS[skill])

        return sorted(list(matched_skills))

    @classmethod
    def normalize_skill(cls, skill_name: str) -> str:
        """
        Normalizes a single skill input string into its canonical equivalent.
        Returns the original skill if not matched in the canonical dictionary.
        """
        if not skill_name:
            return ""

        cls._initialize()
        cleaned = skill_name.strip()
        lower = cleaned.lower()

        return cls._alias_map.get(lower, cleaned)
