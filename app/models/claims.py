"""Claim models and validation results."""

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class ClaimType(str, Enum):
    DIRECT_FACT = "DIRECT_FACT"
    ANALYTICAL_INFERENCE = "ANALYTICAL_INFERENCE"


class Claim(BaseModel):
    claim_id: str
    section_id: str
    text: str
    claim_type: ClaimType = ClaimType.DIRECT_FACT
    evidence_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
    is_valid: bool = False
    validation_notes: list[str] = Field(default_factory=list)


class ClaimValidationResult(BaseModel):
    is_valid: bool
    total_claims: int
    valid_claims: int
    unsupported_claims: list[str] = Field(default_factory=list)
    invalid_evidence_ids: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
