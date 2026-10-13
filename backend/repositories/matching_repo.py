from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.repositories.models import MatchResultModel
from backend.schemas.matching import MatchResultData


class MatchResultRepository:
    """Repository for MatchResult persistence."""

    @staticmethod
    def save_or_update(
        db: Session,
        analysis_id: str,
        data: MatchResultData,
    ) -> MatchResultModel:
        existing = db.scalar(
            select(MatchResultModel).where(MatchResultModel.candidate_id == data.candidate_id)
        )
        if not existing:
            result = MatchResultModel(
                candidate_id=data.candidate_id,
                analysis_id=analysis_id,
                match_score=data.match_score,
                rank=data.rank,
                component_scores=data.breakdown.model_dump(),
                matching_evidence={
                    "required_skills": data.required_skills.model_dump(),
                    "preferred_skills": data.preferred_skills.model_dump(),
                    "experience_evidence": [e.model_dump() for e in data.experience_evidence],
                },
                scoring_config_version=data.config_version,
            )
            db.add(result)
        else:
            result = existing
            result.match_score = data.match_score
            result.rank = data.rank
            result.component_scores = data.breakdown.model_dump()
            result.matching_evidence = {
                "required_skills": data.required_skills.model_dump(),
                "preferred_skills": data.preferred_skills.model_dump(),
                "experience_evidence": [e.model_dump() for e in data.experience_evidence],
            }
            result.scoring_config_version = data.config_version
            result.updated_at = datetime.now(UTC)

        db.commit()
        db.refresh(result)
        return result

    @staticmethod
    def get_by_candidate_id(db: Session, candidate_id: str) -> MatchResultModel | None:
        return db.scalar(
            select(MatchResultModel).where(MatchResultModel.candidate_id == candidate_id)
        )

    @staticmethod
    def list_by_analysis(db: Session, analysis_id: str) -> list[MatchResultModel]:
        return list(
            db.scalars(
                select(MatchResultModel)
                .where(MatchResultModel.analysis_id == analysis_id)
                .order_by(MatchResultModel.rank.asc().nulls_last())
            ).all()
        )


MatchingRepository = MatchResultRepository
