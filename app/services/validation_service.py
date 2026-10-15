"""Deterministic Claim and Citation Validation Service."""

import logging
from app.models.claims import Claim, ClaimValidationResult
from app.models.reports import FinalReport, SectionDraft
from app.models.research import QuestionStatus, ResearchQuestion
from app.services.evidence_registry import EvidenceRegistry

logger = logging.getLogger(__name__)


class ValidationService:
    """Enforces deterministic citation integrity and completion criteria."""

    @staticmethod
    def validate_claims(
        claims: list[Claim],
        registry: EvidenceRegistry,
        run_id: str | None = None,
    ) -> ClaimValidationResult:
        """Validates that all claims reference existing, verified evidence records from the correct run."""
        total_claims = len(claims)
        valid_claims = 0
        unsupported_claims: list[str] = []
        invalid_evidence_ids: list[str] = []
        errors: list[str] = []

        for claim in claims:
            # Check 1: claim must reference at least one evidence ID
            if not claim.evidence_ids:
                unsupported_claims.append(claim.claim_id)
                errors.append(f"Claim '{claim.claim_id}' has no referenced evidence IDs.")
                claim.is_valid = False
                continue

            # Check 2: each referenced evidence ID must exist in registry and belong to the run
            claim_evidence_valid = True
            for eid in claim.evidence_ids:
                ev_record = registry.get_evidence(eid)
                if not ev_record:
                    invalid_evidence_ids.append(eid)
                    errors.append(f"Claim '{claim.claim_id}' references non-existent evidence_id '{eid}'.")
                    claim_evidence_valid = False
                elif ev_record.validation_status != "VALID":
                    errors.append(f"Claim '{claim.claim_id}' references invalid evidence_id '{eid}'.")
                    claim_evidence_valid = False
                elif run_id and ev_record.run_id and ev_record.run_id != run_id:
                    errors.append(
                        f"Claim '{claim.claim_id}' references cross-run evidence_id '{eid}' "
                        f"(evidence run '{ev_record.run_id}' != claim run '{run_id}')."
                    )
                    claim_evidence_valid = False

            if claim_evidence_valid:
                valid_claims += 1
                claim.is_valid = True
            else:
                unsupported_claims.append(claim.claim_id)
                claim.is_valid = False

        is_valid = (len(unsupported_claims) == 0 and len(invalid_evidence_ids) == 0 and total_claims > 0)

        return ClaimValidationResult(
            is_valid=is_valid,
            total_claims=total_claims,
            valid_claims=valid_claims,
            unsupported_claims=unsupported_claims,
            invalid_evidence_ids=invalid_evidence_ids,
            errors=errors,
        )

    @staticmethod
    def evaluate_completion(
        questions: list[ResearchQuestion],
        claims_result: ClaimValidationResult,
        sections: list[SectionDraft],
    ) -> tuple[bool, list[str]]:
        """Determines whether a research run satisfies all invariants for COMPLETE status."""
        limitations: list[str] = []

        # Invariant 1: 100% of required questions must be SUPPORTED
        for q in questions:
            if q.status != QuestionStatus.SUPPORTED:
                limitations.append(
                    f"Question '{q.question_id}' is '{q.status.value}': {q.unresolved_reason or 'Missing evidence'}"
                )

        # Invariant 2: Claims validation must pass with zero invalid evidence IDs
        if not claims_result.is_valid:
            limitations.append(
                f"Citation validation failed: {len(claims_result.unsupported_claims)} unsupported claims, "
                f"{len(claims_result.invalid_evidence_ids)} invalid evidence IDs."
            )

        # Invariant 3: Section drafts must exist
        if not sections:
            limitations.append("Report has no synthesized section drafts.")

        can_complete = (len(limitations) == 0)
        return can_complete, limitations
