from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.repositories.models import CandidateModel, MatchResultModel
from backend.schemas.candidate import CandidateExtractedData


class CandidateRepository:
    """Repository for Candidate persistence, safe retrieval, and label assignment."""

    @staticmethod
    def create(
        db: Session,
        analysis_id: str,
        resume_id: str,
        data: CandidateExtractedData,
    ) -> CandidateModel:
        candidate = CandidateModel(
            analysis_id=analysis_id,
            resume_id=resume_id,
            candidate_name=data.identity.name,
            contact_email=data.identity.contact.email,
            contact_phone=data.identity.contact.phone,
            contact_other=data.identity.contact.other,
            extracted_skills=data.skills,
            extracted_experience=[e.model_dump() for e in data.experience],
            extracted_projects=[p.model_dump() for p in data.projects],
            extracted_education=[ed.model_dump() for ed in data.education],
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
        return candidate

    @staticmethod
    def get_by_id(db: Session, candidate_id: str) -> CandidateModel | None:
        return db.scalar(select(CandidateModel).where(CandidateModel.id == candidate_id))

    @staticmethod
    def list_by_analysis(db: Session, analysis_id: str) -> list[CandidateModel]:
        return list(
            db.scalars(
                select(CandidateModel)
                .where(CandidateModel.analysis_id == analysis_id)
                .order_by(CandidateModel.created_at.asc())
            ).all()
        )

    @staticmethod
    def assign_labels_and_ranks(
        db: Session,
        analysis_id: str,
        ranked_candidate_ids: list[str],
    ) -> None:
        """
        Assigns sequential candidate labels and ranks inside finalization.
        Labels (Candidate 01, Candidate 02) are ordered strictly by random candidate ID,
        ensuring zero dependence on rank, filename, or demographics.
        """
        # Fetch all candidates for this analysis
        candidates = list(
            db.scalars(
                select(CandidateModel)
                .where(CandidateModel.analysis_id == analysis_id)
                .order_by(CandidateModel.id.asc())  # Order by random ID
            ).all()
        )

        # 1. Assign display labels sequentially based on candidate ID ordering (only if unassigned)
        for idx, candidate in enumerate(candidates, start=1):
            if not candidate.display_label:
                candidate.display_label = f"Candidate {idx:02d}"
                candidate.updated_at = datetime.now(UTC)

        # 2. Assign ranks to match results
        for rank, cid in enumerate(ranked_candidate_ids, start=1):
            db.execute(
                update(MatchResultModel)
                .where(
                    MatchResultModel.analysis_id == analysis_id,
                    MatchResultModel.candidate_id == cid,
                )
                .values(rank=rank, updated_at=datetime.now(UTC))
            )

        db.commit()
