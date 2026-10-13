from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.repositories.models import ExplanationModel
from backend.schemas.common import ExplanationState


class ExplanationRepository:
    """Repository for Explanation lifecycle management and persistence."""

    @staticmethod
    def get_by_candidate_id(db: Session, candidate_id: str) -> ExplanationModel | None:
        return db.scalar(
            select(ExplanationModel).where(ExplanationModel.candidate_id == candidate_id)
        )

    @staticmethod
    def start_generation_conditional(
        db: Session, candidate_id: str, analysis_id: str
    ) -> bool:
        """
        Atomically transitions state to GENERATING only from NOT_REQUESTED or FAILED.
        Prevents concurrent generation requests.
        """
        existing = db.scalar(
            select(ExplanationModel).where(ExplanationModel.candidate_id == candidate_id)
        )
        now = datetime.now(UTC)

        if not existing:
            # Create new row in GENERATING state
            explanation = ExplanationModel(
                candidate_id=candidate_id,
                analysis_id=analysis_id,
                state=ExplanationState.GENERATING.value,
                generation_started_at=now,
            )
            db.add(explanation)
            db.commit()
            return True

        if existing.state in [
            ExplanationState.NOT_REQUESTED.value,
            ExplanationState.FAILED.value,
        ]:
            stmt = (
                update(ExplanationModel)
                .where(
                    ExplanationModel.candidate_id == candidate_id,
                    ExplanationModel.state.in_([
                        ExplanationState.NOT_REQUESTED.value,
                        ExplanationState.FAILED.value,
                    ]),
                )
                .values(
                    state=ExplanationState.GENERATING.value,
                    generation_started_at=now,
                    failure_reason=None,
                    updated_at=now,
                )
            )
            res = db.execute(stmt)
            db.commit()
            return res.rowcount > 0

        return False

    @staticmethod
    def save_explanation(
        db: Session, candidate_id: str, content: dict
    ) -> None:
        db.execute(
            update(ExplanationModel)
            .where(ExplanationModel.candidate_id == candidate_id)
            .values(
                state=ExplanationState.READY.value,
                explanation_content=content,
                failure_reason=None,
                updated_at=datetime.now(UTC),
            )
        )
        db.commit()

    @staticmethod
    def mark_failed(db: Session, candidate_id: str, reason: str) -> None:
        db.execute(
            update(ExplanationModel)
            .where(ExplanationModel.candidate_id == candidate_id)
            .values(
                state=ExplanationState.FAILED.value,
                failure_reason=reason,
                updated_at=datetime.now(UTC),
            )
        )
        db.commit()
