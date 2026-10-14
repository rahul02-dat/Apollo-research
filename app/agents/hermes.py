"""Hermes Evidence and Gap Analysis Agent."""

import logging
from app.models.gaps import CoverageAssessment, GapRequest
from app.models.research import QuestionStatus, ResearchQuestion
from app.services.evidence_registry import EvidenceRegistry
from app.services.gap_detection import GapDetectionService

logger = logging.getLogger(__name__)


class HermesAnalysisAgent:
    """Evaluates question-level evidence coverage and generates targeted follow-up requests."""

    def __init__(self, evidence_registry: EvidenceRegistry) -> None:
        self.evidence_registry = evidence_registry

    def evaluate_coverage(
        self,
        run_id: str,
        questions: list[ResearchQuestion],
        current_round: int = 0,
        max_rounds: int = 3,
    ) -> tuple[CoverageAssessment, list[ResearchQuestion]]:
        """Evaluates whether all required research questions have valid evidence."""
        return GapDetectionService.evaluate_coverage(
            run_id=run_id,
            questions=questions,
            registry=self.evidence_registry,
            current_round=current_round,
            max_rounds=max_rounds,
        )

    def identify_next_followup(self, assessment: CoverageAssessment) -> GapRequest | None:
        """Picks the highest-priority gap for targeted follow-up retrieval."""
        if not assessment.gaps:
            return None
        return assessment.gaps[0]
