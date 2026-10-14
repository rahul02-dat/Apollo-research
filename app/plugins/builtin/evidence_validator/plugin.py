"""Built-in Evidence Validator Plugin."""

import logging
from app.models.evidence import EvidenceRecord, EvidenceValidationStatus
from app.models.sources import SourceDocument
from app.plugins.manifest import PluginManifest

logger = logging.getLogger(__name__)


class EvidenceValidatorPlugin:
    """Deterministic validation of evidence provenance, units, and consistency."""

    def __init__(self) -> None:
        self.manifest = PluginManifest(
            plugin_id="financial_checks",
            display_name="Financial Evidence & Context Validator",
            version="1.0.0",
            api_version="1.0",
            plugin_type="evidence_validator",
            capabilities=["evidence.financial.validate"],
            required_permissions=[],
            config_schema={},
            enabled_by_default=True,
        )

    def validate(
        self,
        evidence: list[EvidenceRecord],
        sources: dict[str, SourceDocument],
    ) -> list[EvidenceRecord]:
        """Performs deterministic checks on evidence records."""
        validated: list[EvidenceRecord] = []

        for record in evidence:
            errors: list[str] = []

            # 1. Provenance check: source_id must exist in registered sources
            if not record.source_id or record.source_id not in sources:
                errors.append(f"Provenance failure: source_id '{record.source_id}' does not resolve to a registered source document.")

            # 2. Content check: must have either excerpt or numeric value
            if not record.excerpt and record.value is None:
                errors.append("Evidence record contains neither a textual excerpt nor a numeric fact.")

            # 3. Numeric context check
            if record.value is not None:
                if not record.unit:
                    errors.append("Numeric financial fact is missing an explicit unit/currency.")
                if not record.period_end:
                    errors.append("Numeric financial fact is missing an explicit reporting period end date.")

            # 4. Locator check
            if not record.locator:
                errors.append("Evidence record is missing a source locator.")

            status = EvidenceValidationStatus.INVALID if errors else EvidenceValidationStatus.VALID
            validated.append(
                record.model_copy(
                    update={
                        "validation_status": status,
                        "validation_errors": errors,
                    }
                )
            )

        return validated


def create_plugin() -> EvidenceValidatorPlugin:
    return EvidenceValidatorPlugin()
