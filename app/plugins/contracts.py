"""Plugin Contracts and Typed Interfaces."""

from pathlib import Path
from typing import Any, Protocol, runtime_checkable
from pydantic import BaseModel
from app.models.claims import Claim
from app.models.evidence import EvidenceRecord
from app.models.reports import FinalReport, ReportArtifact, SectionDraft
from app.models.research import ResearchQuestion, SectionDefinition
from app.models.sources import SourceDocument, SourceDocumentRef, SourceQuery
from app.plugins.manifest import PluginManifest


@runtime_checkable
class Plugin(Protocol):
    manifest: PluginManifest


@runtime_checkable
class SourceConnector(Plugin, Protocol):
    def resolve_issuer(self, identifier: str) -> dict[str, Any]:
        """Resolves ticker or company name to verified CIK and metadata."""
        ...

    def search(self, query: SourceQuery) -> list[SourceDocumentRef]:
        """Discovers filings matching query parameters."""
        ...

    def fetch(self, source: SourceDocumentRef) -> bytes:
        """Fetches raw filing content."""
        ...

    def get_company_facts(self, cik: str) -> dict[str, Any]:
        """Retrieves structured XBRL company facts."""
        ...


@runtime_checkable
class DocumentExtractor(Plugin, Protocol):
    def extract(
        self,
        content: bytes | str,
        document_ref: SourceDocumentRef,
        questions: list[ResearchQuestion] | None = None,
    ) -> list[EvidenceRecord]:
        """Extracts structured evidence records from raw document content."""
        ...


@runtime_checkable
class EvidenceValidator(Plugin, Protocol):
    def validate(
        self,
        evidence: list[EvidenceRecord],
        sources: dict[str, SourceDocument],
    ) -> list[EvidenceRecord]:
        """Validates evidence provenance, units, and consistency."""
        ...


@runtime_checkable
class FinancialAnalytics(Plugin, Protocol):
    def compute_metrics(
        self,
        evidence: list[EvidenceRecord],
    ) -> dict[str, Any]:
        """Computes deterministic financial metrics and ratios."""
        ...


@runtime_checkable
class ModelProvider(Plugin, Protocol):
    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Generates text from prompt."""
        ...

    def generate_structured(
        self,
        prompt: str,
        schema: type[BaseModel],
        system_prompt: str | None = None,
    ) -> BaseModel:
        """Generates structured response adhering to Pydantic schema."""
        ...


@runtime_checkable
class SynthesisStrategy(Plugin, Protocol):
    def synthesize_section(
        self,
        section: SectionDefinition,
        evidence: list[EvidenceRecord],
        questions: list[ResearchQuestion],
        model_provider: ModelProvider,
    ) -> SectionDraft:
        """Synthesizes a report section from approved evidence."""
        ...


@runtime_checkable
class ReportExporter(Plugin, Protocol):
    def export(self, report: FinalReport, output_path: Path | str) -> ReportArtifact:
        """Exports validated report model to an output artifact."""
        ...
