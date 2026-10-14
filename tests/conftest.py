"""Pytest configuration, fixtures, and mock plugins."""

import json
from pathlib import Path
from typing import Any
import pytest
from app.models.reports import FinalReport, ReportArtifact
from app.models.sources import SourceDocumentRef, SourceQuery
from app.plugins.manifest import PluginManifest
from app.plugins.registry import PluginRegistry
from app.plugins.builtin import register_builtin_plugins
from app.services.evidence_registry import EvidenceRegistry


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def sample_company_facts() -> dict[str, Any]:
    with open(FIXTURES_DIR / "sample_company_facts.json", "r") as f:
        return json.load(f)


@pytest.fixture
def sample_html_content() -> bytes:
    with open(FIXTURES_DIR / "sample_10k_excerpt.html", "rb") as f:
        return f.read()


@pytest.fixture
def plugin_registry() -> PluginRegistry:
    reg = PluginRegistry()
    register_builtin_plugins(reg)
    return reg


@pytest.fixture
def evidence_registry() -> EvidenceRegistry:
    return EvidenceRegistry()


class FakeSourcePlugin:
    """Deterministic mock source plugin for AT-14 substitution testing."""

    def __init__(self, sample_html: bytes, sample_facts: dict[str, Any]) -> None:
        self.sample_html = sample_html
        self.sample_facts = sample_facts
        self.manifest = PluginManifest(
            plugin_id="fake_source",
            display_name="Deterministic Fake Source Plugin",
            version="1.0.0",
            api_version="1.0",
            plugin_type="source_connector",
            capabilities=[
                "sec.issuer.resolve",
                "sec.filings.search",
                "sec.filings.fetch",
                "sec.facts.fetch",
            ],
            enabled_by_default=True,
        )

    def resolve_issuer(self, identifier: str) -> dict[str, Any]:
        if identifier.upper() in ["INVALID", "NONEXISTENT", "XXXX"]:
            from app.connectors.sec_edgar_client import SECResourceNotFoundError
            raise SECResourceNotFoundError(f"Unknown issuer: {identifier}")
        return {
            "ticker": "MSFT",
            "cik": "0000789019",
            "title": "MICROSOFT CORPORATION",
        }

    def search(self, query: SourceQuery) -> list[SourceDocumentRef]:
        return [
            SourceDocumentRef(
                plugin_id="fake_source",
                source_id="SEC_10-K_0000789019_24_000078",
                title="Microsoft Corp Form 10-K (2024-07-30)",
                url="https://www.sec.gov/Archives/edgar/data/789019/000078901924000078/msft-20240630.htm",
                source_type="SEC_FILING",
                form_type="10-K",
                accession_number="0000789019-24-000078",
                filing_date="2024-07-30",
                period_of_report="2024-06-30",
            )
        ]

    def fetch(self, source: SourceDocumentRef) -> bytes:
        return self.sample_html

    def get_company_facts(self, cik: str) -> dict[str, Any]:
        return self.sample_facts


class FakeMarkdownExporterPlugin:
    """Alternative exporter plugin for AT-17 substitution testing."""

    def __init__(self) -> None:
        self.manifest = PluginManifest(
            plugin_id="markdown_exporter",
            display_name="Markdown Report Exporter",
            version="1.0.0",
            api_version="1.0",
            plugin_type="report_exporter",
            capabilities=["report.markdown.export"],
            enabled_by_default=True,
        )

    def export(self, report: FinalReport, output_path: Any = None) -> ReportArtifact:
        md_text = f"# {report.company_name} Research Report\n\n{report.executive_summary}\n"
        return ReportArtifact(
            artifact_id=f"ART_MD_{report.run_id[:8]}",
            run_id=report.run_id,
            format="MARKDOWN",
            file_path="/tmp/test_report.md",
            sha256="fake_sha256",
            file_size_bytes=len(md_text),
            is_complete=report.is_complete,
        )


@pytest.fixture
def fake_source(sample_html_content: bytes, sample_company_facts: dict[str, Any]) -> FakeSourcePlugin:
    return FakeSourcePlugin(sample_html_content, sample_company_facts)


@pytest.fixture
def fake_exporter() -> FakeMarkdownExporterPlugin:
    return FakeMarkdownExporterPlugin()
