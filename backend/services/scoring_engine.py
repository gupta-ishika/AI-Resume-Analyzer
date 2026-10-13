import re
from dataclasses import dataclass

from backend.schemas.candidate import ScoringProfile
from backend.schemas.common import (
    EducationMatch,
    EducationMatchStatus,
    ScoreComponent,
    ScoreComponentStatus,
)
from backend.schemas.matching import (
    ExperienceEvidenceItem,
    MatchingProfile,
    MatchResultData,
    ScoreBreakdown,
    SkillMatchEvidence,
)
from backend.services.embedding_service import (
    EmbeddingService,
    default_embedding_service,
)


@dataclass(frozen=True)
class ScoringConfig:
    """Versioned scoring configuration defining weights and parameters."""

    required_skill_weight: float = 0.35
    preferred_skill_weight: float = 0.15
    relevant_experience_weight: float = 0.25
    semantic_relevance_weight: float = 0.25
    version: str = "1.0.0"


class ScoringEngine:
    """
    Deterministic scoring engine calculating multi-component match results.
    Owned by Person 2 per ARCHITECTURE.md.
    Strictly operates on ScoringProfile and MatchingProfile without any LLM dependencies.
    """

    def __init__(
        self,
        config: ScoringConfig | None = None,
        embedding_service: EmbeddingService | None = None,
    ):
        self.config = config or ScoringConfig()
        self.embedding_service = embedding_service or default_embedding_service

    def score_candidate(
        self,
        candidate_id: str,
        profile: ScoringProfile,
        matching_profile: MatchingProfile,
    ) -> MatchResultData:
        """
        Calculates deterministic component scores and weighted composite match score.
        """
        candidate_skills_lower = {s.lower() for s in profile.skills}

        # 1. Required Skill Coverage
        req_matched: list[str] = []
        req_missing: list[str] = []
        if matching_profile.required_skills:
            for s in matching_profile.required_skills:
                if s.lower() in candidate_skills_lower:
                    req_matched.append(s)
                else:
                    req_missing.append(s)
            req_coverage_val = round(
                (len(req_matched) / len(matching_profile.required_skills)) * 100.0, 2
            )
            req_comp = ScoreComponent(
                status=ScoreComponentStatus.SCORED,
                value=req_coverage_val,
            )
        else:
            req_comp = ScoreComponent(status=ScoreComponentStatus.NOT_SPECIFIED, value=None)

        # 2. Preferred Skill Coverage
        pref_matched: list[str] = []
        pref_missing: list[str] = []
        if matching_profile.preferred_skills:
            for s in matching_profile.preferred_skills:
                if s.lower() in candidate_skills_lower:
                    pref_matched.append(s)
                else:
                    pref_missing.append(s)
            pref_coverage_val = round(
                (len(pref_matched) / len(matching_profile.preferred_skills)) * 100.0, 2
            )
            pref_comp = ScoreComponent(
                status=ScoreComponentStatus.SCORED,
                value=pref_coverage_val,
            )
        else:
            pref_comp = ScoreComponent(status=ScoreComponentStatus.NOT_SPECIFIED, value=None)

        # 3. Relevant Experience Score & Evidence
        candidate_total_years = self._calculate_candidate_years(profile)
        req_years = self._extract_required_years(matching_profile.experience_requirements)

        exp_evidence = [
            ExperienceEvidenceItem(
                summary=f"{exp.title} ({exp.years or exp.duration or 'duration unstated'}): "
                f"{'; '.join(exp.responsibilities[:2]) if exp.responsibilities else 'N/A'}"
            )
            for exp in profile.experience
            if exp.title
        ]

        if not matching_profile.experience_requirements:
            exp_comp = ScoreComponent(status=ScoreComponentStatus.NOT_SPECIFIED, value=None)
        elif req_years is not None and req_years > 0:
            exp_ratio = min(1.0, candidate_total_years / req_years)
            exp_val = round(exp_ratio * 100.0, 2)
            exp_comp = ScoreComponent(status=ScoreComponentStatus.SCORED, value=exp_val)
        else:
            # Experience required without explicit number of years
            exp_val = 100.0 if candidate_total_years > 0 or len(profile.experience) > 0 else 0.0
            exp_comp = ScoreComponent(status=ScoreComponentStatus.SCORED, value=exp_val)

        # 4. Semantic Relevance Score
        c_text = profile.job_relevant_text.strip()
        j_text = matching_profile.job_relevant_text.strip()

        if not c_text or not j_text:
            sem_comp = ScoreComponent(status=ScoreComponentStatus.NOT_SPECIFIED, value=None)
        else:
            c_vec = self.embedding_service.embed(c_text)
            j_vec = self.embedding_service.embed(j_text)
            cos_sim = self.embedding_service.similarity(c_vec, j_vec)
            # Map cosine similarity (0.0 to 1.0) to 0-100 scale
            sem_val = round(max(0.0, min(1.0, cos_sim)) * 100.0, 2)
            sem_comp = ScoreComponent(status=ScoreComponentStatus.SCORED, value=sem_val)

        # 5. Education Matching
        edu_match = self._evaluate_education(profile, matching_profile)

        # 6. Composite Score Calculation (weighted, dynamic re-normalization)
        active_components: list[tuple[float, float]] = []  # (value, weight)

        if req_comp.status == ScoreComponentStatus.SCORED and req_comp.value is not None:
            active_components.append((req_comp.value, self.config.required_skill_weight))

        if pref_comp.status == ScoreComponentStatus.SCORED and pref_comp.value is not None:
            active_components.append((pref_comp.value, self.config.preferred_skill_weight))

        if exp_comp.status == ScoreComponentStatus.SCORED and exp_comp.value is not None:
            active_components.append((exp_comp.value, self.config.relevant_experience_weight))

        if sem_comp.status == ScoreComponentStatus.SCORED and sem_comp.value is not None:
            active_components.append((sem_comp.value, self.config.semantic_relevance_weight))

        total_weight = sum(w for _, w in active_components)
        if total_weight > 0.0:
            final_score = sum((v * (w / total_weight)) for v, w in active_components)
            match_score = round(max(0.0, min(100.0, final_score)), 2)
        else:
            match_score = 0.0

        breakdown = ScoreBreakdown(
            semantic_relevance=sem_comp,
            required_skill_coverage=req_comp,
            preferred_skill_coverage=pref_comp,
            relevant_experience=exp_comp,
            education=edu_match,
        )

        return MatchResultData(
            candidate_id=candidate_id,
            match_score=match_score,
            rank=None,
            breakdown=breakdown,
            required_skills=SkillMatchEvidence(matched=req_matched, missing=req_missing),
            preferred_skills=SkillMatchEvidence(matched=pref_matched, missing=pref_missing),
            experience_evidence=exp_evidence,
            config_version=self.config.version,
        )

    def _calculate_candidate_years(self, profile: ScoringProfile) -> float:
        """Sums candidate experience years or extracts from duration strings."""
        total = 0.0
        for exp in profile.experience:
            if exp.years is not None and exp.years > 0:
                total += exp.years
            elif exp.duration:
                m = re.search(r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)", exp.duration, re.IGNORECASE)
                if m:
                    total += float(m.group(1))
        return total

    def _extract_required_years(self, requirements: list[str]) -> float | None:
        """Extracts required years of experience from requirement strings."""
        for req in requirements:
            m = re.search(r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)", req, re.IGNORECASE)
            if m:
                return float(m.group(1))
        return None

    def _evaluate_education(
        self,
        profile: ScoringProfile,
        matching_profile: MatchingProfile,
    ) -> EducationMatch:
        """Evaluates whether candidate degrees meet JD education requirements."""
        if not matching_profile.education_requirements:
            return EducationMatch(
                status=EducationMatchStatus.NOT_SPECIFIED,
                notes="No explicit education requirement specified in job requirements.",
            )

        combined_req = " ".join(matching_profile.education_requirements).lower()
        candidate_degrees = [
            f"{ed.degree or ''} {ed.field_of_study or ''}".lower()
            for ed in profile.education
        ]
        all_candidate_edu = " ".join(candidate_degrees)

        # Check degree level hierarchy
        degree_keywords = [
            ("phd", ["phd", "ph.d", "doctorate"]),
            ("master", ["master", "m.s", "ms", "m.tech", "mba"]),
            ("bachelor", ["bachelor", "b.s", "bs", "b.tech", "b.e", "degree"]),
        ]

        req_level = None
        for level, kw_list in degree_keywords:
            if any(kw in combined_req for kw in kw_list):
                req_level = level
                break

        if not req_level:
            # Generic requirement found, check any degree presence
            if profile.education:
                return EducationMatch(
                    status=EducationMatchStatus.MET,
                    notes="Candidate holds required educational qualification.",
                )
            return EducationMatch(
                status=EducationMatchStatus.NOT_MET,
                notes="Candidate has no recorded education matching requirement.",
            )

        # Level hierarchy: phd (3) >= master (2) >= bachelor (1)
        level_ranks = {"bachelor": 1, "master": 2, "phd": 3}
        target_rank = level_ranks.get(req_level, 1)

        candidate_max_rank = 0
        for level, kw_list in degree_keywords:
            if any(kw in all_candidate_edu for kw in kw_list):
                cand_rank = level_ranks.get(level, 1)
                if cand_rank > candidate_max_rank:
                    candidate_max_rank = cand_rank

        if candidate_max_rank >= target_rank:
            return EducationMatch(
                status=EducationMatchStatus.MET,
                notes=f"Candidate educational background meets or exceeds {req_level} requirement.",
            )

        return EducationMatch(
            status=EducationMatchStatus.NOT_MET,
            notes=f"Candidate education does not satisfy required {req_level} level.",
        )
