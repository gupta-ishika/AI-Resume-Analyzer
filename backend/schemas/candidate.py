from pydantic import BaseModel, Field


class CandidateContact(BaseModel):
    email: str | None = None
    phone: str | None = None
    other: list[str] = Field(default_factory=list)


class CandidateIdentity(BaseModel):
    name: str = "Unknown Candidate"
    contact: CandidateContact = Field(default_factory=CandidateContact)


class ExperienceItem(BaseModel):
    title: str
    company: str | None = None
    duration: str | None = None
    years: float = 0.0
    responsibilities: list[str] = Field(default_factory=list)


class EducationItem(BaseModel):
    degree: str
    field_of_study: str | None = None
    institution: str | None = None


class ProjectItem(BaseModel):
    name: str
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)


class CandidateExtractedData(BaseModel):
    identity: CandidateIdentity = Field(default_factory=CandidateIdentity)
    skills: list[str] = Field(default_factory=list)
    experience: list[ExperienceItem] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)


class ScoringProfile(BaseModel):
    """
    Candidate representation permitted into matching.
    MUST NOT contain names, contact details, pronouns, or institution names.
    """
    skills: list[str] = Field(default_factory=list)
    experience: list[ExperienceItem] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)
    job_relevant_text: str = ""
