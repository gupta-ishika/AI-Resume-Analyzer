from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from backend.repositories.models import AnalysisModel
from backend.schemas.common import AnalysisStatus


class AnalysisRepository:
    """Repository for managing Analysis persistence and lifecycle transitions."""

    @staticmethod
    def create(db: Session, name: str, scoring_config_version: str = "1.0.0") -> AnalysisModel:
        analysis = AnalysisModel(
            name=name,
            status=AnalysisStatus.REQUIREMENTS_PENDING.value,
            scoring_config_version=scoring_config_version,
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        return analysis

    @staticmethod
    def get_by_id(
        db: Session, analysis_id: str, include_deleted: bool = False
    ) -> AnalysisModel | None:
        query = select(AnalysisModel).where(AnalysisModel.id == analysis_id)
        if not include_deleted:
            query = query.where(AnalysisModel.deletion_requested_at.is_(None))
        return db.scalar(query)

    @staticmethod
    def list_active(
        db: Session, page: int = 1, limit: int = 20
    ) -> tuple[list[AnalysisModel], int]:
        base_query = select(AnalysisModel).where(AnalysisModel.deletion_requested_at.is_(None))

        # Total count
        total = db.scalar(select(func.count()).select_from(base_query.subquery())) or 0

        # Paged items ordered by updated_at descending
        offset = max(0, (page - 1) * limit)
        items = (
            db.scalars(
                base_query.order_by(AnalysisModel.updated_at.desc())
                .offset(offset)
                .limit(limit)
            )
            .all()
        )
        return list(items), total

    @staticmethod
    def update_status_conditional(
        db: Session,
        analysis_id: str,
        from_status: str,
        to_status: str,
        failure_reason: str | None = None,
    ) -> bool:
        """
        Atomically updates analysis status if and only if current status matches from_status.
        Returns True if the transition succeeded, False if current status did not match.
        """
        stmt = (
            update(AnalysisModel)
            .where(
                AnalysisModel.id == analysis_id,
                AnalysisModel.status == from_status,
                AnalysisModel.deletion_requested_at.is_(None),
            )
            .values(
                status=to_status,
                failure_reason=failure_reason,
                updated_at=datetime.now(UTC),
            )
        )
        result = db.execute(stmt)
        db.commit()
        return result.rowcount > 0

    @staticmethod
    def mark_for_deletion(db: Session, analysis_id: str) -> bool:
        """
        Marks an analysis for deletion if not currently PROCESSING.
        Returns True if marked, False if not found or already PROCESSING.
        """
        stmt = (
            update(AnalysisModel)
            .where(
                AnalysisModel.id == analysis_id,
                AnalysisModel.status != AnalysisStatus.PROCESSING.value,
                AnalysisModel.deletion_requested_at.is_(None),
            )
            .values(
                deletion_requested_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        result = db.execute(stmt)
        db.commit()
        return result.rowcount > 0

    @staticmethod
    def delete_permanently(db: Session, analysis_id: str) -> None:
        analysis = db.scalar(select(AnalysisModel).where(AnalysisModel.id == analysis_id))
        if analysis:
            db.delete(analysis)
            db.commit()
