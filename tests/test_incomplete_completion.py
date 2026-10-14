"""Acceptance Test AT-10: Incomplete Research Enforcement."""

import pytest
from app.models.claims import Claim, ClaimType
from app.models.reports import SectionDraft
from app.models.research import QuestionStatus, ResearchItinerary, ResearchQuestion, ResearchRun, RunStatus, SectionDefinition
from app.plugins.builtin.model_provider.plugin import MockModelProvider
from app.plugins.builtin.synthesis_strategy.plugin import FinancialSynthesisPlugin
from app.services.evidence_registry import EvidenceRegistry
from app.services.report_service import ReportService


def test_at10_unresolved_question_prevents_complete(evidence_registry: EvidenceRegistry) -> None:
    run = ResearchRun(
        run_id="RUN_AT10",
        company_name="MICROSOFT CORPORATION",
        ticker="MSFT",
        objective="Analyze performance and unannounced future plans",
    )

    # An itinerary where one required question is UNRESOLVED
    q_resolved = ResearchQuestion(
        question_id="Q_01",
        section_id="SEC_01",
        question="What were revenues?",
        status=QuestionStatus.SUPPORTED,
    )
    q_unresolved = ResearchQuestion(
        question_id="Q_02",
        section_id="SEC_01",
        question="What are confidential internal board minutes?",
        status=QuestionStatus.UNRESOLVED,
        unresolved_reason="Information not available in public SEC filings.",
    )

    itinerary = ResearchItinerary(
        itinerary_id="ITIN_AT10",
        run_id="RUN_AT10",
        company_name="MICROSOFT CORPORATION",
        ticker="MSFT",
        cik="0000789019",
        sections=[
            SectionDefinition(
                section_id="SEC_01",
                title="Operations",
                description="Operations",
                question_ids=["Q_01", "Q_02"],
            )
        ],
        questions=[q_resolved, q_unresolved],
    )

    # Draft section noting the unresolved question
    draft = SectionDraft(
        section_id="SEC_01",
        title="Operations",
        narrative="Operational analysis...",
        claims=[
            Claim(
                claim_id="CLM_01",
                section_id="SEC_01",
                text="Revenues were reported.",
                claim_type=ClaimType.DIRECT_FACT,
                evidence_ids=[],  # No evidence
            )
        ],
        evidence_ids=[],
        source_ids=[],
        unresolved_questions=["Q_02"],
    )

    synthesis_plugin = FinancialSynthesisPlugin()
    model_provider = MockModelProvider()
    report_service = ReportService(evidence_registry, synthesis_plugin, model_provider)

    final_report = report_service.assemble_report(run, itinerary, [draft])

    # Core Invariant: Status MUST NOT be COMPLETE
    assert final_report.status == RunStatus.INCOMPLETE
    assert final_report.is_complete is False
    assert len(final_report.unresolved_limitations) > 0
    assert any("Q_02" in lim for lim in final_report.unresolved_limitations)
