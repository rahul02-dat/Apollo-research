"""Acceptance Test AT-09: Mandatory Two-Stage Synthesis Pipeline."""

from decimal import Decimal
import pytest
from app.models.evidence import EvidenceRecord, EvidenceValidationStatus
from app.models.reports import SectionDraft
from app.models.research import ResearchItinerary, ResearchQuestion, ResearchRun, RunStatus, SectionDefinition
from app.models.sources import SourceDocument
from app.plugins.builtin.model_provider.plugin import MockModelProvider
from app.plugins.builtin.synthesis_strategy.plugin import FinancialSynthesisPlugin
from app.services.evidence_registry import EvidenceRegistry
from app.services.report_service import ReportService


def test_at09_two_stage_synthesis(evidence_registry: EvidenceRegistry) -> None:
    # 1. Register sources and evidence
    source = SourceDocument(
        source_id="SRC_10K_2024",
        issuer_cik="0000789019",
        accession_number="0000789019-24-000078",
        form_type="10-K",
        filed_at="2024-07-30",
        period_of_report="2024-06-30",
        title="Form 10-K",
        source_url="https://sec.gov",
    )
    evidence_registry.add_source(source)

    ev_rev = EvidenceRecord(
        evidence_id="EV_REV_2024",
        source_id="SRC_10K_2024",
        locator="XBRL us-gaap:Revenues",
        fact_name="Revenues",
        value=Decimal("245122000000"),
        unit="USD",
        period_end="2024-06-30",
        question_ids=["Q_REV"],
        validation_status=EvidenceValidationStatus.VALID,
    )
    evidence_registry.add_evidence(ev_rev)

    run = ResearchRun(
        run_id="RUN_AT09",
        company_name="MICROSOFT CORPORATION",
        ticker="MSFT",
        cik="0000789019",
        objective="Analyze performance",
    )

    itinerary = ResearchItinerary(
        itinerary_id="ITIN_AT09",
        run_id="RUN_AT09",
        company_name="MICROSOFT CORPORATION",
        ticker="MSFT",
        cik="0000789019",
        sections=[
            SectionDefinition(
                section_id="SEC_PERF",
                title="Financial Performance",
                description="Revenue analysis",
                question_ids=["Q_REV"],
            )
        ],
        questions=[
            ResearchQuestion(
                question_id="Q_REV",
                section_id="SEC_PERF",
                question="What was total revenue?",
                evidence_ids=["EV_REV_2024"],
                status="SUPPORTED",
            )
        ],
    )

    synthesis_plugin = FinancialSynthesisPlugin()
    model_provider = MockModelProvider()
    report_service = ReportService(evidence_registry, synthesis_plugin, model_provider)

    # Stage 1: Generate section drafts independently
    section_drafts = report_service.synthesize_sections(run, itinerary)
    assert len(section_drafts) == 1
    draft = section_drafts[0]
    assert isinstance(draft, SectionDraft)
    assert draft.section_id == "SEC_PERF"
    assert len(draft.claims) > 0
    assert "EV_REV_2024" in draft.evidence_ids
    assert "SRC_10K_2024" in draft.source_ids

    # Stage 2: Assemble complete report from section drafts
    final_report = report_service.assemble_report(run, itinerary, section_drafts)
    assert final_report.run_id == run.run_id
    assert len(final_report.sections) == 1
    assert final_report.status == RunStatus.COMPLETE
    assert final_report.is_complete is True
    assert len(final_report.bibliography) == 1
    assert final_report.bibliography[0].source_id == "SRC_10K_2024"
    assert "Executive Summary" in final_report.executive_summary
