from backend.schemas.matching import MatchingProfile
from backend.schemas.requirements import JobRequirements


class MatchingProfileBuilder:
    """
    Constructs a MatchingProfile from recruiter-confirmed JobRequirements.
    Owned by Person 2 per ARCHITECTURE.md.
    """

    @classmethod
    def build_matching_profile(
        cls,
        requirements: JobRequirements,
        enforce_confirmed: bool = True,
    ) -> MatchingProfile:
        """
        Builds the matching view from recruiter-confirmed requirements.
        Enforces that unconfirmed requirements are not used for scoring and ranking.
        Preserves explicit and unspecified requirements.
        """
        if enforce_confirmed and not requirements.confirmed_at:
            raise ValueError(
                "Job requirements must be confirmed by recruiter before building matching profile"
            )

        # Build job_relevant_text if not explicitly provided
        job_text = requirements.job_relevant_text.strip() if requirements.job_relevant_text else ""
        if not job_text:
            text_parts: list[str] = []
            if requirements.required_skills:
                text_parts.append(f"Required Skills: {', '.join(requirements.required_skills)}")
            if requirements.preferred_skills:
                text_parts.append(f"Preferred Skills: {', '.join(requirements.preferred_skills)}")
            if requirements.experience_requirements:
                text_parts.append(
                    f"Experience: {' '.join(requirements.experience_requirements)}"
                )
            if requirements.education_requirements:
                text_parts.append(
                    f"Education: {' '.join(requirements.education_requirements)}"
                )
            if requirements.explicit_requirements:
                text_parts.append(
                    f"Other Requirements: {' '.join(requirements.explicit_requirements)}"
                )
            job_text = "\n".join(text_parts)

        return MatchingProfile(
            required_skills=list(requirements.required_skills or []),
            preferred_skills=list(requirements.preferred_skills or []),
            experience_requirements=list(requirements.experience_requirements or []),
            education_requirements=list(requirements.education_requirements or []),
            explicit_requirements=list(requirements.explicit_requirements or []),
            job_relevant_text=job_text,
        )
