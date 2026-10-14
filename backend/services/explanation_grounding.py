import re
from datetime import UTC, datetime

from backend.schemas.explanation import ExplanationData
from backend.services.skill_extractor import SkillExtractor


class GroundingViolation(Exception):
    """Raised when an explanation violates factual grounding rules."""


class ExplanationGroundingService:
    """
    Grounding validation service for LLM-generated explanations (LLM-01).
    Ensures that AI explanations are strictly grounded in deterministic matching evidence
    and extracted candidate profile, without hallucinated skills or personal data leaks.
    """

    @classmethod
    def validate_grounding(
        cls,
        explanation: ExplanationData,
        candidate_skills: list[str],
        matched_skills: list[str],
        missing_required: list[str],
        missing_preferred: list[str],
        candidate_name: str | None = None,
    ) -> tuple[bool, ExplanationData | None, list[str]]:
        """
        Validates an ExplanationData against ground truth structured evidence:
        1. Ensures no candidate PII (name, email, phone) appears in the generated text.
        2. Ensures strengths do not cite hallucinated skills absent from the candidate profile.
        3. Ensures gaps do not contradict matched skills.
        4. Validates that assessment and experience_alignment are substantive and non-empty.

        Returns (is_valid, validated_explanation, violations_list).
        """
        violations: list[str] = []

        # 1. Non-empty check
        if not explanation.assessment or not explanation.assessment.strip():
            violations.append("Assessment is empty.")
        if not explanation.experience_alignment or not explanation.experience_alignment.strip():
            violations.append("Experience alignment is empty.")

        # 2. PII Leakage Check
        all_text = " ".join([
            *explanation.strengths,
            *explanation.gaps,
            explanation.experience_alignment,
            explanation.assessment,
        ])

        if candidate_name and len(candidate_name.strip()) > 2:
            name_parts = [p for p in candidate_name.strip().split() if len(p) > 2]
            for part in name_parts:
                pattern = rf"\b{re.escape(part)}\b"
                if re.search(pattern, all_text, re.IGNORECASE):
                    violations.append(f"PII Leak: Candidate name '{part}' appeared in explanation.")
                    break

        # Check for emails or phone numbers
        if re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", all_text):
            violations.append("PII Leak: Email address detected in explanation.")
        if re.search(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", all_text):
            violations.append("PII Leak: Phone number detected in explanation.")

        # Canonical skill sets for grounding comparison (case-insensitive matching)
        known_candidate_skills = {
            s.lower() for s in candidate_skills
        } | {
            s.lower() for s in matched_skills
        }
        known_matched_skills = {s.lower() for s in matched_skills}

        # 3. Grounding of Strengths:
        # Check every strength for technical skill claims that are completely absent from candidate
        grounded_strengths: list[str] = []
        for strength in explanation.strengths:
            extracted_in_strength = SkillExtractor.extract_skills(strength)
            ungrounded_skills = [
                s for s in extracted_in_strength if s.lower() not in known_candidate_skills
            ]

            if ungrounded_skills:
                violations.append(
                    f"Ungrounded claim in strength: skills {ungrounded_skills} "
                    "do not exist in candidate profile."
                )
            else:
                grounded_strengths.append(strength)

        # 4. Contradiction in Gaps:
        # If a gap claims a candidate lacks a matched skill, that's a contradiction!
        grounded_gaps: list[str] = []
        for gap in explanation.gaps:
            extracted_in_gap = SkillExtractor.extract_skills(gap)
            contradicted_skills = [
                s for s in extracted_in_gap if s.lower() in known_matched_skills
            ]

            if contradicted_skills:
                violations.append(
                    f"Contradictory gap claim: skills {contradicted_skills} "
                    "were successfully matched in candidate evidence."
                )
            else:
                grounded_gaps.append(gap)

        # 5. Outcome determination
        # Severe violations: PII leak or contradicted claims
        if any("PII Leak" in v for v in violations):
            return False, None, violations

        if any("Contradictory" in v for v in violations):
            return False, None, violations

        # If more than 50% of claimed strengths are ungrounded hallucinations, reject entirely
        if explanation.strengths and len(grounded_strengths) == 0 and len(violations) > 0:
            violations.append("All cited strengths were ungrounded hallucinations.")
            return False, None, violations

        # Construct validated and cleansed ExplanationData
        validated = ExplanationData(
            strengths=grounded_strengths,
            gaps=grounded_gaps,
            experience_alignment=explanation.experience_alignment.strip(),
            assessment=explanation.assessment.strip(),
            generated_at=explanation.generated_at or datetime.now(UTC),
        )

        return True, validated, violations
