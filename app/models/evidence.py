"""Evidence record models."""

from decimal import Decimal
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class EvidenceValidationStatus(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    UNCHECKED = "UNCHECKED"


class EvidenceRecord(BaseModel):
    evidence_id: str
    source_id: str
    locator: str  # section name, XBRL tag, table identifier
    excerpt: str | None = None
    question_ids: list[str] = Field(default_factory=list)
    fact_name: str | None = None
    value: Decimal | None = None
    unit: str | None = None  # USD, shares, percent
    period_start: str | None = None
    period_end: str | None = None
    fiscal_period: str | None = None  # FY2023, Q3 2024
    validation_status: EvidenceValidationStatus = EvidenceValidationStatus.UNCHECKED
    validation_errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
