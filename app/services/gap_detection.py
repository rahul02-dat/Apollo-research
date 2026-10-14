"""Deterministic Knowledge Gap Detection Service for Hermes."""

from datetime import datetime, timezone
import logging
from app.models.gaps import CoverageAssessment, FollowUpRequest, GapRequest
from app.models.evidence import EvidenceValidationStatus
from app.models.research import QuestionStatus, ResearchQuestion
from app.services.evidence_registry import EvidenceRegistry

logger = logging.getLogger(__name__)


class GapDetectionService:
    """Evaluates question-level coverage and generates structured gap requests."""

    @staticmethod
    def evaluate_coverage(
        run_id: str,
        questions: list[ResearchQuestion],
        registry: EvidenceRegistry,
        current_round: int = 0,
        max_rounds: int = 3,
    ) -> tuple[CoverageAssessment, list[ResearchQuestion]]:
        """Evaluates whether each research question is supported by validated evidence."""
        updated_questions: list[ResearchQuestion] = []
        gaps: list[GapRequest] = []

        supported_count = 0
        gap_count = 0
        unanswered_count = 0
        unresolved_count = 0

        for q in questions:
            # Query registry for evidence linked to this question
            evidence_records = registry.get_evidence_for_question(q.question_id)
            valid_evidence = [
                e for e in evidence_records
                if e.validation_status == EvidenceValidationStatus.VALID
            ]

            q_copy = q.model_copy()

            if valid_evidence:
                q_copy.status = QuestionStatus.SUPPORTED
                q_copy.evidence_ids = [e.evidence_id for e in valid_evidence]
                q_copy.unresolved_reason = None
                supported_count += 1
            else:
                # Evidence is missing
                if current_round >= max_rounds:
                    q_copy.status = QuestionStatus.UNRESOLVED
                    q_copy.unresolved_reason = (
                        f"Autonomous follow-up limit reached ({max_rounds} rounds) without resolving required evidence."
                    )
                    unresolved_count += 1
                else:
                    q_copy.status = QuestionStatus.GAP
                    gap_count += 1

                    # Generate targeted follow-up request based on question content
                    follow_up = GapDetectionService._create_targeted_followup(q_copy)
                    gap_req = GapRequest(
                        question_id=q_copy.question_id,
                        status=QuestionStatus.GAP,
                        reason=f"Question '{q_copy.question}' lacks validated primary-source evidence in registered filings.",
                        follow_up=follow_up,
                        attempt_round=current_round + 1,
                    )
                    gaps.append(gap_req)

            updated_questions.append(q_copy)

        is_fully_supported = (supported_count == len(questions)) and len(questions) > 0

        assessment = CoverageAssessment(
            run_id=run_id,
            evaluated_at=datetime.now(timezone.utc).isoformat(),
            total_questions=len(questions),
            supported_count=supported_count,
            gap_count=gap_count,
            unanswered_count=unanswered_count,
            unresolved_count=unresolved_count,
            gaps=gaps,
            is_fully_supported=is_fully_supported,
        )

        logger.info(
            "Coverage assessment for run %s: %d/%d supported, %d gaps, %d unresolved",
            run_id, supported_count, len(questions), gap_count, unresolved_count,
        )

        return assessment, updated_questions

    @staticmethod
    def _create_targeted_followup(question: ResearchQuestion) -> FollowUpRequest:
        """Constructs specific targeted retrieval requirements for an unsupported question."""
        text = question.question.lower()

        if any(term in text for term in ["segment", "division", "geography", "unit"]):
            return FollowUpRequest(
                filing_types=["10-K", "10-Q"],
                target_sections=["Segment Information", "Item 7 Management's Discussion"],
                required_evidence=["Revenue by reportable segment", "Operating income by reportable segment"],
                terms=["segment reporting", "reportable segments", "segment revenue"],
            )

        if any(term in text for term in ["liquidity", "debt", "cash flow", "credit", "borrowing"]):
            return FollowUpRequest(
                filing_types=["10-K", "10-Q"],
                target_sections=["Liquidity and Capital Resources", "Item 8 Note on Debt"],
                required_evidence=["Cash and cash equivalents", "Long-term debt maturities", "Operating cash flow"],
                terms=["liquidity", "capital resources", "debt obligations"],
            )

        if any(term in text for term in ["risk", "uncertaint", "threat", "litigation"]):
            return FollowUpRequest(
                filing_types=["10-K", "10-Q"],
                target_sections=["Item 1A Risk Factors"],
                required_evidence=["Material operational, legal, and macroeconomic risks"],
                terms=["risk factors", "material risks"],
            )

        if any(term in text for term in ["revenue", "profit", "margin", "income", "sales"]):
            return FollowUpRequest(
                filing_types=["10-K", "10-Q"],
                target_sections=["Item 7 Management's Discussion", "Item 8 Financial Statements"],
                required_evidence=["Consolidated Statement of Income", "Revenue growth rates", "Operating margin"],
                terms=["results of operations", "net income", "operating revenue"],
            )

        return FollowUpRequest(
            filing_types=["10-K", "10-Q", "8-K"],
            target_sections=["Item 1 Business", "Item 7 MD&A"],
            required_evidence=[question.question],
            terms=[word for word in question.question.split() if len(word) > 4][:3],
        )
