"""Evidence record models."""

from decimal import Decimal
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class EvidenceValidationStatus(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    UNCHECKED = "UNCHECKED"


class EvidenceType(str, Enum):
    NARRATIVE_PASSAGE = "NARRATIVE_PASSAGE"
    NUMERIC_FACT = "NUMERIC_FACT"
    TABLE_CELL = "TABLE_CELL"


class EvidenceRecord(BaseModel):
    evidence_id: str
    source_id: str
    run_id: str | None = None
    workspace_id: str | None = None
    source_url: str | None = None
    locator: str  # section name, XBRL tag, table identifier
    excerpt: str | None = None
    question_ids: list[str] = Field(default_factory=list)
    fact_name: str | None = None
    value: Decimal | None = None
    unit: str | None = None  # USD, shares, percent
    period_start: str | None = None
    period_end: str | None = None
    fiscal_period: str | None = None  # FY2023, Q3 2024
    evidence_type: EvidenceType = EvidenceType.NARRATIVE_PASSAGE
    validation_status: EvidenceValidationStatus = EvidenceValidationStatus.UNCHECKED
    validation_errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def __init__(self, **data: Any) -> None:
        if "context_snippet" in data and "excerpt" not in data:
            data["excerpt"] = data["context_snippet"]
        if "period" in data and "period_end" not in data:
            data["period_end"] = data["period"]
        super().__init__(**data)

    @property
    def period(self) -> str | None:
        return self.period_end or self.fiscal_period or self.period_start

    @property
    def context_snippet(self) -> str | None:
        return self.excerpt


