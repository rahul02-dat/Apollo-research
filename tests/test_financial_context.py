"""Acceptance Test AT-07: Financial Context Preservation and Unit Validation."""

from decimal import Decimal
import pytest
from app.models.evidence import EvidenceRecord, EvidenceValidationStatus
from app.models.sources import SourceDocument
from app.plugins.builtin.evidence_validator.plugin import EvidenceValidatorPlugin


def test_at07_financial_context_preservation() -> None:
    validator = EvidenceValidatorPlugin()

    sources = {
        "SRC_01": SourceDocument(
            source_id="SRC_01",
            issuer_cik="0000789019",
            accession_number="0000789019-24-000078",
            form_type="10-K",
            filed_at="2024-07-30",
            period_of_report="2024-06-30",
            title="Form 10-K",
            source_url="https://sec.gov",
        )
    }

    # 1. Valid financial fact
    valid_record = EvidenceRecord(
        evidence_id="EV_VALID_01",
        source_id="SRC_01",
        locator="XBRL us-gaap:Revenues",
        fact_name="Revenues",
        value=Decimal("245122000000"),
        unit="USD",
        period_start="2023-07-01",
        period_end="2024-06-30",
        fiscal_period="FY 2024",
    )

    # 2. Fact missing unit
    missing_unit = EvidenceRecord(
        evidence_id="EV_NO_UNIT",
        source_id="SRC_01",
        locator="XBRL us-gaap:Revenues",
        fact_name="Revenues",
        value=Decimal("245122000000"),
        unit=None,  # Missing unit
        period_end="2024-06-30",
    )

    # 3. Fact missing reporting period end date
    missing_period = EvidenceRecord(
        evidence_id="EV_NO_PERIOD",
        source_id="SRC_01",
        locator="XBRL us-gaap:Revenues",
        fact_name="Revenues",
        value=Decimal("245122000000"),
        unit="USD",
        period_end=None,  # Missing period
    )

    # 4. Fact referencing nonexistent source
    bad_source = EvidenceRecord(
        evidence_id="EV_BAD_SRC",
        source_id="SRC_NONEXISTENT",
        locator="XBRL us-gaap:Revenues",
        fact_name="Revenues",
        value=Decimal("245122000000"),
        unit="USD",
        period_end="2024-06-30",
    )

    results = validator.validate([valid_record, missing_unit, missing_period, bad_source], sources)

    # Valid fact must pass
    assert results[0].validation_status == EvidenceValidationStatus.VALID
    assert isinstance(results[0].value, Decimal)
    assert results[0].unit == "USD"
    assert results[0].fiscal_period == "FY 2024"

    # Missing unit must be flagged INVALID
    assert results[1].validation_status == EvidenceValidationStatus.INVALID
    assert any("missing an explicit unit" in err for err in results[1].validation_errors)

    # Missing period must be flagged INVALID
    assert results[2].validation_status == EvidenceValidationStatus.INVALID
    assert any("missing an explicit reporting period" in err for err in results[2].validation_errors)

    # Nonexistent source must be flagged INVALID
    assert results[3].validation_status == EvidenceValidationStatus.INVALID
    assert any("Provenance failure" in err for err in results[3].validation_errors)
