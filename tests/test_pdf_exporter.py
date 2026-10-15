"""Acceptance Test AT-11: PDF Generation and Clickable Primary-Source Citations."""

from pathlib import Path
import pytest
from app.models.reports import BibliographyItem, FinalReport, ReportArtifact, SectionDraft
from app.models.research import RunStatus
from app.plugins.builtin.pdf_exporter.plugin import PDFExporterPlugin


def test_at11_pdf_generation_with_clickable_citations(tmp_path: Path) -> None:
    plugin = PDFExporterPlugin()

    bib_item = BibliographyItem(
        source_id="SRC_SEC_10K_2024",
        title="Microsoft Corporation Form 10-K",
        form_type="10-K",
        filed_at="2024-07-30",
        period_of_report="2024-06-30",
        source_url="https://www.sec.gov/Archives/edgar/data/789019/000078901924000078/msft-20240630.htm",
        accession_number="0000789019-24-000078",
    )

    section = SectionDraft(
        section_id="SEC_PERF",
        title="Financial Performance & Revenue",
        narrative="Total revenue reached $245.1 billion for fiscal year 2024 as disclosed in SRC_SEC_10K_2024.",
        claims=[],
        evidence_ids=["EV_01"],
        source_ids=["SRC_SEC_10K_2024"],
        unresolved_questions=[],
        is_valid=True,
    )

    report = FinalReport(
        report_id="RPT_AT11",
        run_id="RUN_AT11",
        company_name="MICROSOFT CORPORATION",
        ticker="MSFT",
        cik="0000789019",
        objective="Analyze performance",
        status=RunStatus.COMPLETE,
        executive_summary="Executive Summary\n\nVerified annual performance from official SEC filings.",
        sections=[section],
        bibliography=[bib_item],
        unresolved_limitations=[],
        is_complete=True,
        validation_passed=True,
    )

    pdf_path = tmp_path / "test_apollo_report.pdf"
    artifact = plugin.export(report, output_path=pdf_path)

    assert isinstance(artifact, ReportArtifact)
    assert artifact.format == "PDF"
    assert artifact.file_size_bytes > 1000
    assert Path(artifact.file_path).exists()
    assert artifact.is_complete is True

    # Read PDF header bytes
    with open(artifact.file_path, "rb") as f:
        content = f.read()
    assert content.startswith(b"%PDF-")
    # Verify that the canonical SEC URL is embedded inside the PDF stream
    assert b"https://www.sec.gov/Archives/edgar/data" in content


def test_pdf_generation_with_vector_charts(tmp_path: Path) -> None:
    plugin = PDFExporterPlugin()

    bib_item = BibliographyItem(
        source_id="SRC_SEC_10K_2024",
        title="Microsoft Corporation Form 10-K",
        form_type="10-K",
        filed_at="2024-07-30",
        period_of_report="2024-06-30",
        source_url="https://www.sec.gov/Archives/edgar/data/789019/000078901924000078/msft-20240630.htm",
        accession_number="0000789019-24-000078",
    )

    section = SectionDraft(
        section_id="SEC_PERF",
        title="Financial Performance & Revenue",
        narrative="Multi-year financial metrics indicate sustained compound growth.",
        claims=[],
        evidence_ids=["EV_01"],
        source_ids=["SRC_SEC_10K_2024"],
        unresolved_questions=[],
        is_valid=True,
    )

    charts_data = {
        "revenue_trend": {
            "title": "Annual Revenue Trend (2-Year)",
            "labels": ["FY 2022", "FY 2023", "FY 2024"],
            "raw_values": [198270000000.0, 211915000000.0, 245122000000.0],
            "values_in_billions": [198.27, 211.92, 245.12],
            "unit": "USD Billions",
            "cagr_formatted": "+11.19%",
        },
        "margin_trend": {
            "title": "Operating & Net Profit Margin Trajectory (%)",
            "labels": ["FY 2022", "FY 2023", "FY 2024"],
            "operating_margins": [42.06, 41.77, 44.64],
            "net_margins": [36.69, 34.15, 35.96],
            "unit": "%",
        },
        "capital_structure": {
            "title": "Capital Structure & Liquidity Breakdown",
            "labels": ["Total Assets", "Total Liabilities", "Cash & Equivalents"],
            "raw_values": [512163000000.0, 243686000000.0, 75535000000.0],
            "values_in_billions": [512.16, 243.69, 75.54],
            "unit": "USD Billions",
        },
    }

    report = FinalReport(
        report_id="RPT_CHARTS",
        run_id="RUN_CHARTS",
        company_name="MICROSOFT CORPORATION",
        ticker="MSFT",
        cik="0000789019",
        objective="Analyze performance with charts",
        status=RunStatus.COMPLETE,
        executive_summary="Executive Summary with embedded vector charts.",
        sections=[section],
        bibliography=[bib_item],
        financial_metrics={"charts": charts_data},
        unresolved_limitations=[],
        is_complete=True,
        validation_passed=True,
    )

    pdf_path = tmp_path / "test_apollo_charts_report.pdf"
    artifact = plugin.export(report, output_path=pdf_path)

    assert isinstance(artifact, ReportArtifact)
    assert artifact.file_size_bytes > 4000
    assert Path(artifact.file_path).exists()
    assert artifact.is_complete is True

    with open(artifact.file_path, "rb") as f:
        pdf_bytes = f.read()

    assert pdf_bytes.startswith(b"%PDF-")
    assert b"/Type /Page" in pdf_bytes

