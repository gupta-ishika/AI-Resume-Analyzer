from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.repositories.models import JobRequirementsModel
from backend.schemas.requirements import JobRequirements


class JobRequirementsRepository:
    """Repository for storing and retrieving JobRequirements."""

    @staticmethod
    def get_by_analysis_id(db: Session, analysis_id: str) -> JobRequirementsModel | None:
        return db.scalar(
            select(JobRequirementsModel).where(JobRequirementsModel.analysis_id == analysis_id)
        )

    @staticmethod
    def save_or_update(
        db: Session, analysis_id: str, reqs: JobRequirements
    ) -> JobRequirementsModel:
        model = JobRequirementsRepository.get_by_analysis_id(db, analysis_id)
        if not model:
            model = JobRequirementsModel(
                analysis_id=analysis_id,
                required_skills=reqs.required_skills,
                preferred_skills=reqs.preferred_skills,
                experience_requirements=reqs.experience_requirements,
                education_requirements=reqs.education_requirements,
                explicit_requirements=reqs.explicit_requirements,
                job_relevant_text=reqs.job_relevant_text,
                confirmed_at=reqs.confirmed_at,
            )
            db.add(model)
        else:
            model.required_skills = reqs.required_skills
            model.preferred_skills = reqs.preferred_skills
            model.experience_requirements = reqs.experience_requirements
            model.education_requirements = reqs.education_requirements
            model.explicit_requirements = reqs.explicit_requirements
            model.job_relevant_text = reqs.job_relevant_text
            model.confirmed_at = reqs.confirmed_at
            model.updated_at = datetime.now(UTC)

        db.commit()
        db.refresh(model)
        return model
