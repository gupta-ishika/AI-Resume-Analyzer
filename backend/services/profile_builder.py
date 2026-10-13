from backend.schemas.candidate import (
    CandidateExtractedData,
    EducationItem,
    ExperienceItem,
    ProjectItem,
    ScoringProfile,
)
from backend.services.pii_scrubber import PIIScrubber


class ProfileBuilder:
    """
    Constructs a sanitized, fairness-controlled ScoringProfile from candidate data.
    Owned by Person 2 per ARCHITECTURE.md.
    """

    @classmethod
    def build_scoring_profile(cls, candidate: CandidateExtractedData) -> ScoringProfile:
        name = candidate.identity.name
        email = candidate.identity.contact.email
        phone = candidate.identity.contact.phone

        institutions = [
            ed.institution for ed in candidate.education if ed.institution
        ]

        # 1. Scrub experience responsibilities
        sanitized_experience: list[ExperienceItem] = []
        for exp in candidate.experience:
            scrubbed_responsibilities = [
                PIIScrubber.scrub_text(
                    resp,
                    name=name,
                    email=email,
                    phone=phone,
                    institutions=institutions,
                )
                for resp in exp.responsibilities
            ]
            sanitized_experience.append(
                ExperienceItem(
                    title=PIIScrubber.scrub_text(
                        exp.title,
                        name=name,
                        email=email,
                        phone=phone,
                        institutions=institutions,
                    ),
                    company=None,  # Company names removed to prevent brand bias
                    duration=exp.duration,
                    years=exp.years,
                    responsibilities=[r for r in scrubbed_responsibilities if r],
                )
            )

        # 2. Scrub project descriptions
        sanitized_projects: list[ProjectItem] = []
        for proj in candidate.projects:
            scrubbed_desc = (
                PIIScrubber.scrub_text(
                    proj.description,
                    name=name,
                    email=email,
                    phone=phone,
                    institutions=institutions,
                )
                if proj.description
                else None
            )
            sanitized_projects.append(
                ProjectItem(
                    name=proj.name,
                    description=scrubbed_desc,
                    technologies=proj.technologies,
                )
            )

        # 3. Anonymize education (preserve degree level, remove institution names)
        sanitized_education: list[EducationItem] = [
            EducationItem(
                degree=ed.degree,
                field_of_study=ed.field_of_study,
                institution=None,  # Institution removed per ARCHITECTURE.md Section 8
            )
            for ed in candidate.education
        ]

        # 4. Construct job_relevant_text only from approved professional sections
        text_parts: list[str] = []

        if candidate.skills:
            text_parts.append("Skills: " + ", ".join(candidate.skills))

        for exp in sanitized_experience:
            if exp.title:
                text_parts.append(exp.title)
            if exp.responsibilities:
                text_parts.extend(exp.responsibilities)

        for proj in sanitized_projects:
            if proj.description:
                text_parts.append(proj.description)

        raw_job_text = "\n".join(text_parts)
        scrubbed_job_relevant_text = PIIScrubber.scrub_text(
            raw_job_text,
            name=name,
            email=email,
            phone=phone,
            institutions=institutions,
        )

        return ScoringProfile(
            skills=candidate.skills,
            experience=sanitized_experience,
            projects=sanitized_projects,
            education=sanitized_education,
            job_relevant_text=scrubbed_job_relevant_text,
        )
