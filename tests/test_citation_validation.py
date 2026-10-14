"""Acceptance Test AT-08: Citation Integrity and Grounding Verification."""

from decimal import Decimal
import pytest
from app.models.claims import Claim, ClaimType
from app.models.evidence import EvidenceRecord, EvidenceValidationStatus
from app.services.evidence_registry import EvidenceRegistry
from app.services.validation_service import ValidationService


def test_at08_citation_integrity(evidence_registry: EvidenceRegistry) -> None:
    # 1. Register a genuine valid evidence record
    real_evidence = EvidenceRecord(
        evidence_id="EV_GENUINE_01",
        source_id="SRC_SEC_01",
        locator="Item 7 MD&A",
        excerpt="Operating income was $109.4 billion",
        value=Decimal("109400000000"),
        unit="USD",
        period_end="2024-06-30",
        validation_status=EvidenceValidationStatus.VALID,
    )
    evidence_registry.add_evidence(real_evidence)

    # Claim 1: Fully grounded in genuine evidence -> MUST PASS
    claim_valid = Claim(
        claim_id="CLM_01",
        section_id="SEC_PERF",
        text="Operating income reached $109.4 billion for fiscal 2024.",
        claim_type=ClaimType.DIRECT_FACT,
        evidence_ids=["EV_GENUINE_01"],
    )

    # Claim 2: Fabricated evidence ID -> MUST FAIL
    claim_fabricated_id = Claim(
        claim_id="CLM_02",
        section_id="SEC_PERF",
        text="Company announced $50 billion expansion into quantum computing.",
        claim_type=ClaimType.DIRECT_FACT,
        evidence_ids=["EV_FABRICATED_9999"],  # Non-existent evidence ID
    )

    # Claim 3: Empty evidence IDs -> MUST FAIL
    claim_no_evidence = Claim(
        claim_id="CLM_03",
        section_id="SEC_PERF",
        text="Company claims it is the undisputed leader in every market.",
        claim_type=ClaimType.DIRECT_FACT,
        evidence_ids=[],  # No evidence
    )

    # Validate individual valid claim
    res_valid = ValidationService.validate_claims([claim_valid], evidence_registry)
    assert res_valid.is_valid is True
    assert res_valid.valid_claims == 1
    assert len(res_valid.unsupported_claims) == 0

    # Validate claims containing fabricated evidence
    res_fabricated = ValidationService.validate_claims([claim_valid, claim_fabricated_id], evidence_registry)
    assert res_fabricated.is_valid is False
    assert "EV_FABRICATED_9999" in res_fabricated.invalid_evidence_ids
    assert "CLM_02" in res_fabricated.unsupported_claims

    # Validate claim with no citations
    res_no_evidence = ValidationService.validate_claims([claim_no_evidence], evidence_registry)
    assert res_no_evidence.is_valid is False
    assert "CLM_03" in res_no_evidence.unsupported_claims
