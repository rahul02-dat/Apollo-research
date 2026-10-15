"""Tests for Phase 4: SEC Form 8-K Material Events, Form 4 Insider Trading, and Management Guidance."""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
import pytest

from app.agents.athena import AthenaResearchAgent
from app.connectors.sec_edgar_client import SECEdgarClient
from app.models.events import (
    FORM_8K_ITEM_TITLES,
    InsiderTransaction,
    MaterialEvent,
    ManagementGuidance,
    TranscriptQuote,
)
from app.models.evidence import EvidenceRecord, EvidenceType
from app.models.reports import FinalReport, SectionDraft
from app.models.research import ResearchQuestion, ResearchRun, RunStatus
from app.plugins.builtin import register_builtin_plugins
from app.plugins.builtin.management_transcripts.plugin import ManagementTranscriptsPlugin
from app.plugins.builtin.pdf_exporter.plugin import PDFExporterPlugin
from app.plugins.builtin.sec_material_events.plugin import SECMaterialEventsPlugin
from app.plugins.registry import PluginRegistry
from app.services.evidence_registry import EvidenceRegistry


class FakeSECClientForEvents:
    """Mock SEC EDGAR Client returning 8-K and Form 4 filings."""

    def __init__(self, sample_facts: dict[str, Any], sample_html: bytes) -> None:
        self.sample_facts = sample_facts
        self.sample_html = sample_html

    def get_submissions(self, cik: str) -> dict[str, Any]:
        return {
            "name": "MICROSOFT CORPORATION",
            "cik": cik,
            "filings": {
                "recent": {
                    "form": ["10-K", "8-K", "4", "8-K"],
                    "accessionNumber": [
                        "0000789019-24-000078",
                        "0000789019-24-000095",
                        "0000789019-24-000102",
                        "0000789019-24-000115",
                    ],
                    "filingDate": ["2024-07-30", "2024-08-15", "2024-09-01", "2024-09-20"],
                    "reportDate": ["2024-06-30", "2024-08-15", "2024-09-01", "2024-09-20"],
                    "primaryDocument": ["msft-20240630.htm", "msft-8k-earnings.htm", "doc4.xml", "msft-8k-exec.htm"],
                    "primaryDocDescription": ["10-K", "Form 8-K", "Form 4", "Form 8-K"],
                    "items": ["", "2.02,7.01", "", "5.02"],
                }
            },
        }

    def get_company_facts(self, cik: str) -> dict[str, Any]:
        return self.sample_facts

    def construct_document_url(self, cik: str, accession_number: str, primary_document: str) -> str:
        clean_cik = str(int(cik.strip()))
        acc_clean = accession_number.replace("-", "")
        return f"https://www.sec.gov/Archives/edgar/data/{clean_cik}/{acc_clean}/{primary_document}"

    def fetch_filing_document(self, url: str) -> bytes:
        if "doc4.xml" in url:
            xml_sample = """<?xml version="1.0"?>
            <ownershipDocument>
                <reportingOwner>
                    <reportingOwnerId>
                        <rptOwnerName>Nadella Satya</rptOwnerName>
                    </reportingOwnerId>
                    <reportingOwnerRelationship>
                        <isDirector>1</isDirector>
                        <isOfficer>1</isOfficer>
                        <officerTitle>Chairman and CEO</officerTitle>
                    </reportingOwnerRelationship>
                </reportingOwner>
                <nonDerivativeTransaction>
                    <securityTitle>
                        <value>Common Stock</value>
                    </securityTitle>
                    <transactionDate>
                        <value>2024-09-01</value>
                    </transactionDate>
                    <transactionCoding>
                        <transactionCode>S</transactionCode>
                    </transactionCoding>
                    <transactionAmounts>
                        <transactionShares>
                            <value>50000</value>
                        </transactionShares>
                        <transactionPricePerShare>
                            <value>415.50</value>
                        </transactionPricePerShare>
                        <transactionAcquiredDisposedCode>
                            <value>D</value>
                        </transactionAcquiredDisposedCode>
                    </transactionAmounts>
                </nonDerivativeTransaction>
            </ownershipDocument>
            """
            return xml_sample.encode("utf-8")
        return self.sample_html


def test_form_8k_material_events_parsing(sample_company_facts: dict[str, Any], sample_html_content: bytes) -> None:
    """Verifies parsing of Form 8-K items and canonical URL generation."""
    client = FakeSECClientForEvents(sample_company_facts, sample_html_content)
    plugin = SECMaterialEventsPlugin(client=client)  # type: ignore[arg-type]

    events = plugin.fetch_events("0000789019", limit=5)
    assert len(events) == 2

    # Event 1: Items 2.02, 7.01
    ev1 = events[0]
    assert ev1.form_type == "8-K"
    assert ev1.accession_number == "0000789019-24-000095"
    assert ev1.filing_date == "2024-08-15"
    assert len(ev1.items) == 2
    item_numbers = [it.item_number for it in ev1.items]
    assert "2.02" in item_numbers
    assert "7.01" in item_numbers
    assert "Results of Operations and Financial Condition (Earnings)" in ev1.items[0].item_name
    assert "https://www.sec.gov/Archives/edgar/data/789019/000078901924000095/msft-8k-earnings.htm" == ev1.source_url

    # Event 2: Item 5.02
    ev2 = events[1]
    assert ev2.accession_number == "0000789019-24-000115"
    assert ev2.items[0].item_number == "5.02"
    assert "Departure/Election of Directors or Principal Officers" in ev2.items[0].item_name

    # Convert to EvidenceRecords
    ev_records = plugin.to_evidence_records(events, [])
    assert len(ev_records) == 2
    assert ev_records[0].evidence_type == EvidenceType.NARRATIVE_PASSAGE
    assert "Form 8-K" in ev_records[0].locator
    assert ev_records[0].source_url == ev1.source_url


def test_form_4_insider_transactions_parsing(sample_company_facts: dict[str, Any], sample_html_content: bytes) -> None:
    """Verifies XML parsing of Form 4 insider trading transactions."""
    client = FakeSECClientForEvents(sample_company_facts, sample_html_content)
    plugin = SECMaterialEventsPlugin(client=client)  # type: ignore[arg-type]

    txs = plugin.fetch_insider_transactions("0000789019", limit=5)
    assert len(txs) >= 1

    tx = txs[0]
    assert tx.reporting_owner_name == "Nadella Satya"
    assert tx.relationship_role == "Chairman and CEO"
    assert tx.transaction_date == "2024-09-01"
    assert tx.transaction_code == "S"
    assert tx.transaction_type == "Sale"
    assert tx.shares == 50000.0
    assert tx.price_per_share == 415.50
    assert tx.total_value == 20775000.0
    assert tx.is_acquisition is False
    assert "https://www.sec.gov/Archives/edgar/data/789019/000078901924000102/doc4.xml" == tx.source_url

    # Convert to EvidenceRecords
    records = plugin.to_evidence_records([], txs)
    assert len(records) == 1
    assert records[0].evidence_type == EvidenceType.NUMERIC_FACT
    assert records[0].value == 20775000.0
    assert records[0].unit == "USD"
    assert "Form 4 Non-Derivative Table" in records[0].locator
    assert "Nadella Satya" in records[0].context_snippet


def test_earnings_transcripts_and_management_guidance() -> None:
    """Verifies transcript quote extraction, speaker attribution, and guidance targets."""
    plugin = ManagementTranscriptsPlugin()

    quotes = plugin.fetch_transcripts("MSFT", cik="0000789019")
    assert len(quotes) >= 3
    assert any("Chief Executive Officer" in q.speaker for q in quotes)
    assert any("AI Platform" in q.topic for q in quotes)

    guidance = plugin.extract_guidance("MSFT", cik="0000789019")
    assert len(guidance) >= 3
    metrics = [g.metric for g in guidance]
    assert "Full-Year Revenue Growth" in metrics
    assert "Operating Margin Trajectory" in metrics

    records = plugin.to_evidence_records(quotes, guidance)
    assert len(records) == len(quotes) + len(guidance)
    assert all(r.evidence_type == EvidenceType.NARRATIVE_PASSAGE for r in records)


def test_athena_integration_with_phase4_plugins(
    sample_company_facts: dict[str, Any],
    sample_html_content: bytes,
) -> None:
    """Verifies that Athena retrieves and registers Form 8-K, Form 4, and transcript evidence."""
    registry = PluginRegistry()
    register_builtin_plugins(registry)

    # Substitute fake SEC client that supports 8-K & Form 4
    fake_client = FakeSECClientForEvents(sample_company_facts, sample_html_content)
    custom_events_plugin = SECMaterialEventsPlugin(client=fake_client)  # type: ignore[arg-type]
    registry.register(custom_events_plugin, overwrite=True)

    ev_registry = EvidenceRegistry()
    athena = AthenaResearchAgent(registry=registry, evidence_registry=ev_registry)

    questions = [
        ResearchQuestion(
            question_id="Q_OVERVIEW",
            section_id="SEC_EXEC",
            question="What are the principal developments and material events?",
        )
    ]

    evidence = athena.retrieve_initial_evidence("0000789019", questions=questions)
    assert len(evidence) > 0

    sources = ev_registry.list_sources()
    form_types = [s.form_type for s in sources]
    assert "10-K" in form_types
    assert "8-K" in form_types
    assert "4" in form_types
    assert "EARNINGS_CALL" in form_types

    # Verify evidence records exist for 8-K and Form 4
    has_8k = any(e.metadata.get("event_type") == "MATERIAL_EVENT_8K" for e in evidence)
    has_form4 = any(e.metadata.get("event_type") == "INSIDER_TRANSACTION_4" for e in evidence)
    has_transcript = any(e.metadata.get("event_type") == "EARNINGS_TRANSCRIPT" for e in evidence)

    assert has_8k is True
    assert has_form4 is True
    assert has_transcript is True


def test_pdf_export_with_events_and_insiders(tmp_path: Path) -> None:
    """Verifies that the PDF exporter formats Material Events and Insider Trading tables."""
    report = FinalReport(
        report_id="RPT_PHASE4_TEST",
        run_id="RUN_PHASE4_01",
        company_name="Microsoft Corp",
        ticker="MSFT",
        cik="0000789019",
        objective="Analyze corporate developments and executive insider transactions.",
        status=RunStatus.COMPLETE,
        executive_summary="Executive Summary: Multi-faceted analysis including material Form 8-K disclosures and Form 4 insider trading.",
        sections=[
            SectionDraft(
                section_id="SEC_EXEC",
                title="Executive Overview",
                narrative="Verified primary source disclosures across operations and executive sentiment.",
                claims=[],
                evidence_ids=[],
                source_ids=[],
                is_valid=True,
            )
        ],
        financial_metrics={
            "material_events": [
                {
                    "title": "Form 8-K: Results of Operations & Leadership Update",
                    "summary": "Microsoft disclosed Q4 operational results and appointment of new cloud leadership.",
                    "date": "2024-08-15",
                    "url": "https://www.sec.gov/Archives/edgar/data/789019/000078901924000095/msft-8k.htm",
                    "items": [{"item_number": "2.02"}, {"item_number": "5.02"}],
                }
            ],
            "insider_transactions": [
                {
                    "owner": "Nadella Satya",
                    "role": "Chairman and CEO",
                    "type": "Sale",
                    "code": "S",
                    "shares": 50000.0,
                    "price": 415.50,
                    "total_value": 20775000.0,
                    "date": "2024-09-01",
                    "url": "https://www.sec.gov/Archives/edgar/data/789019/000078901924000102/doc4.xml",
                }
            ],
            "management_guidance": [
                {
                    "topic": "Cloud & AI Outlook",
                    "speaker": "Chief Financial Officer",
                    "text": "Guidance expects 14% constant currency revenue growth.",
                    "url": "https://www.sec.gov",
                }
            ],
        },
        unresolved_limitations=[],
    )

    pdf_plugin = PDFExporterPlugin()
    out_pdf = tmp_path / "test_phase4_report.pdf"
    artifact = pdf_plugin.export(report, output_path=out_pdf)

    assert artifact is not None
    assert Path(artifact.file_path).exists()
    assert artifact.file_size_bytes > 5000
    assert len(artifact.sha256) == 64
