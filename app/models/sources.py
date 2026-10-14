"""Source document models."""

from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field


class SourceQuery(BaseModel):
    query_id: str
    issuer_cik: str | None = None
    terms: list[str] = Field(default_factory=list)
    filing_types: list[str] = Field(default_factory=lambda: ["10-K", "10-Q"])
    period_start: str | None = None
    period_end: str | None = None


class SourceDocumentRef(BaseModel):
    plugin_id: str
    source_id: str
    title: str
    url: str
    source_type: str = "SEC_FILING"
    form_type: str | None = None
    accession_number: str | None = None
    filing_date: str | None = None
    period_of_report: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceDocument(BaseModel):
    source_id: str
    issuer_cik: str
    accession_number: str
    form_type: str
    filed_at: str
    period_of_report: str
    title: str
    source_url: str
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    content_sha256: str | None = None
    raw_content_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
