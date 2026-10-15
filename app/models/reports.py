"""Report models and artifacts."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field
from app.models.claims import Claim
from app.models.research import RunStatus


class SectionDraft(BaseModel):
    section_id: str
    title: str
    narrative: str
    claims: list[Claim] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    synthesis_version: str = "1.0"
    is_valid: bool = False


class BibliographyItem(BaseModel):
    source_id: str
    title: str
    form_type: str
    filed_at: str
    period_of_report: str
    source_url: str
    accession_number: str


class FinalReport(BaseModel):
    report_id: str
    run_id: str
    company_name: str
    ticker: str
    cik: str
    objective: str
    status: RunStatus
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    executive_summary: str
    sections: list[SectionDraft] = Field(default_factory=list)
    bibliography: list[BibliographyItem] = Field(default_factory=list)
    unresolved_limitations: list[str] = Field(default_factory=list)
    financial_metrics: dict[str, Any] = Field(default_factory=dict)
    is_complete: bool = False
    validation_passed: bool = False


class ReportArtifact(BaseModel):
    artifact_id: str
    run_id: str
    format: str = "PDF"
    file_path: str
    sha256: str
    file_size_bytes: int
    is_complete: bool
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
