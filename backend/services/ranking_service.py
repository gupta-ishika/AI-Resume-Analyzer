from sqlalchemy.orm import Session

from backend.repositories.analysis_repo import AnalysisRepository
from backend.repositories.candidate_repo import CandidateRepository
from backend.repositories.matching_repo import MatchResultRepository
from backend.schemas.common import AnalysisStatus
from backend.schemas.matching import MatchResultData


class RankingService:
    """
    Deterministic ranking service enforcing tie-breaking order and candidate labeling.
    Owned by Person 2 per ARCHITECTURE.md.
    """

    @classmethod
    def rank_results(cls, results: list[MatchResultData]) -> list[MatchResultData]:
        """
        Sorts candidate results deterministically according to the agreed tie-breaking hierarchy:
        1. Higher match score
        2. Higher required skill coverage
        3. Higher relevant experience score
        4. Higher semantic relevance
        5. Candidate ID string comparison (ascending)
        """
        if not results:
            return []

        def sort_key(item: MatchResultData):
            score = item.match_score
            req_cov = item.breakdown.required_skill_coverage.value or 0.0
            exp_sc = item.breakdown.relevant_experience.value or 0.0
            sem_sc = item.breakdown.semantic_relevance.value or 0.0
            return (-score, -req_cov, -exp_sc, -sem_sc, item.candidate_id)

        sorted_results = sorted(results, key=sort_key)

        # Assign 1-indexed ranks
        ranked: list[MatchResultData] = []
        for rank, res in enumerate(sorted_results, start=1):
            res_copy = res.model_copy(update={"rank": rank})
            ranked.append(res_copy)

        return ranked

    @classmethod
    def finalize_analysis_ranking(
        cls,
        db: Session,
        analysis_id: str,
        results: list[MatchResultData],
    ) -> list[MatchResultData]:
        """
        Finalizes ranking inside database transaction:
        1. Ranks candidates deterministically.
        2. Persists MatchResult records with ranks.
        3. Assigns permanent anonymous display labels (Candidate 01, Candidate 02)
           strictly ordered by candidate ID.
        4. Updates analysis status to RANKED.
        """
        ranked_results = cls.rank_results(results)

        # 1. Persist match results in DB
        for res in ranked_results:
            MatchResultRepository.save_or_update(
                db=db,
                analysis_id=analysis_id,
                data=res,
            )

        # 2. Assign labels and ranks in candidate repo
        ranked_candidate_ids = [r.candidate_id for r in ranked_results]
        CandidateRepository.assign_labels_and_ranks(
            db=db,
            analysis_id=analysis_id,
            ranked_candidate_ids=ranked_candidate_ids,
        )

        # 3. Transition Analysis status to RANKED
        AnalysisRepository.update_status_conditional(
            db,
            analysis_id,
            from_status=AnalysisStatus.PROCESSING.value,
            to_status=AnalysisStatus.RANKED.value,
        )

        return ranked_results
