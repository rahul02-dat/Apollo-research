"""Built-in Section-Specific Financial Synthesis Strategy Plugin."""

import logging
from app.models.claims import Claim, ClaimType
from app.models.evidence import EvidenceRecord
from app.models.reports import SectionDraft
from app.models.research import ResearchQuestion, SectionDefinition
from app.plugins.contracts import ModelProvider
from app.plugins.manifest import PluginManifest

logger = logging.getLogger(__name__)


class FinancialSynthesisPlugin:
    """Stage 1: Generates section drafts strictly grounded in approved evidence IDs."""

    def __init__(self) -> None:
        self.manifest = PluginManifest(
            plugin_id="financial_synthesis",
            display_name="Financial Research Section Synthesis Strategy",
            version="1.0.0",
            api_version="1.0",
            plugin_type="synthesis_strategy",
            capabilities=["synthesis.sections.generate"],
            required_permissions=[],
            config_schema={},
            enabled_by_default=True,
        )

    def synthesize_section(
        self,
        section: SectionDefinition,
        evidence: list[EvidenceRecord],
        questions: list[ResearchQuestion],
        model_provider: ModelProvider,
    ) -> SectionDraft:
        """Synthesizes an individual section draft from approved evidence."""
        # Find evidence matching section questions
        section_qids = set(section.question_ids)
        section_evidence = [
            e for e in evidence
            if any(qid in section_qids for qid in e.question_ids) or not e.question_ids
        ]

        # Check for unresolved questions
        covered_qids = {qid for e in section_evidence for qid in e.question_ids}
        unresolved = [qid for qid in section_qids if qid not in covered_qids]

        claims: list[Claim] = []
        narrative_paragraphs: list[str] = [f"### {section.title}"]

        if not section_evidence:
            narrative_paragraphs.append(
                f"No verified primary-source evidence was retrieved to support {section.title.lower()}. "
                f"Questions ({', '.join(unresolved)}) remain unaddressed."
            )
            return SectionDraft(
                section_id=section.section_id,
                title=section.title,
                narrative="\n\n".join(narrative_paragraphs),
                claims=[],
                evidence_ids=[],
                source_ids=[],
                unresolved_questions=unresolved,
                is_valid=False,
            )

        # Generate grounded claims from evidence
        used_evidence_ids: list[str] = []
        used_source_ids: set[str] = set()

        for idx, ev in enumerate(section_evidence, 1):
            used_evidence_ids.append(ev.evidence_id)
            used_source_ids.add(ev.source_id)

            if ev.value is not None:
                claim_text = (
                    f"{ev.locator}: {ev.fact_name} was reported as {ev.value} {ev.unit or ''} "
                    f"for {ev.fiscal_period or ev.period_end}."
                )
                claim_type = ClaimType.DIRECT_FACT
            else:
                excerpt_snippet = (ev.excerpt[:180] + "...") if ev.excerpt and len(ev.excerpt) > 180 else (ev.excerpt or "")
                claim_text = f"According to {ev.locator}: \"{excerpt_snippet}\""
                claim_type = ClaimType.DIRECT_FACT

            claim_id = f"CLM_{section.section_id}_{idx}"
            claim = Claim(
                claim_id=claim_id,
                section_id=section.section_id,
                text=claim_text,
                claim_type=claim_type,
                evidence_ids=[ev.evidence_id],
                source_ids=[ev.source_id],
                is_valid=True,
            )
            claims.append(claim)
            narrative_paragraphs.append(f"{claim_text} [Ref: {ev.evidence_id}]")

        # Analytical synthesis paragraph
        inference_claim_id = f"CLM_{section.section_id}_ANALYSIS"
        inference_text = (
            f"Analytical evaluation of {section.title.lower()} indicates verified disclosures "
            f"across {len(section_evidence)} primary evidence items."
        )
        claims.append(
            Claim(
                claim_id=inference_claim_id,
                section_id=section.section_id,
                text=inference_text,
                claim_type=ClaimType.ANALYTICAL_INFERENCE,
                evidence_ids=list(used_evidence_ids),
                source_ids=list(used_source_ids),
                is_valid=True,
            )
        )
        narrative_paragraphs.append(inference_text)

        if unresolved:
            narrative_paragraphs.append(
                f"Note: Research limitation — question(s) {', '.join(unresolved)} could not be fully answered from available filings."
            )

        return SectionDraft(
            section_id=section.section_id,
            title=section.title,
            narrative="\n\n".join(narrative_paragraphs),
            claims=claims,
            evidence_ids=used_evidence_ids,
            source_ids=list(used_source_ids),
            unresolved_questions=unresolved,
            is_valid=True,
        )


def create_plugin() -> FinancialSynthesisPlugin:
    return FinancialSynthesisPlugin()
