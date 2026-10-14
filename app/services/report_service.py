"""Report Assembly and Two-Stage Synthesis Service."""

import logging
from datetime import datetime, timezone
from app.models.claims import Claim
from app.models.reports import BibliographyItem, FinalReport, SectionDraft
from app.models.research import ResearchItinerary, ResearchRun, RunStatus
from app.plugins.contracts import ModelProvider, SynthesisStrategy
from app.services.evidence_registry import EvidenceRegistry
from app.services.validation_service import ValidationService

logger = logging.getLogger(__name__)


class ReportService:
    """Manages Stage 1 section generation and Stage 2 final assembly."""

    def __init__(
        self,
        registry: EvidenceRegistry,
        synthesis_strategy: SynthesisStrategy,
        model_provider: ModelProvider,
    ) -> None:
        self.registry = registry
        self.synthesis_strategy = synthesis_strategy
        self.model_provider = model_provider

    def synthesize_sections(
        self,
        run: ResearchRun,
        itinerary: ResearchItinerary,
    ) -> list[SectionDraft]:
        """Stage 1: Generates individual section drafts from approved evidence."""
        drafts: list[SectionDraft] = []
        all_evidence = self.registry.list_evidence()

        for section_def in itinerary.sections:
            section_questions = [
                q for q in itinerary.questions
                if q.section_id == section_def.section_id or q.question_id in section_def.question_ids
            ]

            draft = self.synthesis_strategy.synthesize_section(
                section=section_def,
                evidence=all_evidence,
                questions=section_questions,
                model_provider=self.model_provider,
            )
            drafts.append(draft)

        logger.info("Stage 1 complete: generated %d section drafts for run %s", len(drafts), run.run_id)
        return drafts

    def assemble_report(
        self,
        run: ResearchRun,
        itinerary: ResearchItinerary,
        section_drafts: list[SectionDraft],
    ) -> FinalReport:
        """Stage 2: Assembles validated section drafts into a cohesive final report."""
        # 1. Collect all claims from drafts
        all_claims: list[Claim] = []
        for d in section_drafts:
            all_claims.extend(d.claims)

        # 2. Validate all claims and citations deterministically
        claims_result = ValidationService.validate_claims(all_claims, self.registry)

        # 3. Compile bibliography from all referenced sources
        used_source_ids = {s_id for d in section_drafts for s_id in d.source_ids}
        # Also include any sources from claims
        for c in all_claims:
            used_source_ids.update(c.source_ids)

        bibliography: list[BibliographyItem] = []
        for sid in sorted(used_source_ids):
            src = self.registry.get_source(sid)
            if src:
                bibliography.append(
                    BibliographyItem(
                        source_id=src.source_id,
                        title=src.title,
                        form_type=src.form_type,
                        filed_at=src.filed_at,
                        period_of_report=src.period_of_report,
                        source_url=src.source_url,
                        accession_number=src.accession_number,
                    )
                )

        # 4. Check completion criteria
        can_complete, limitations = ValidationService.evaluate_completion(
            questions=itinerary.questions,
            claims_result=claims_result,
            sections=section_drafts,
        )

        final_status = RunStatus.COMPLETE if can_complete else RunStatus.INCOMPLETE

        # 5. Build Executive Summary
        exec_summary_parts = [
            f"This research report evaluates {itinerary.company_name} ({itinerary.ticker}, CIK: {itinerary.cik}) "
            f"in response to the research objective: \"{run.objective}\".",
            f"Research was conducted across {len(bibliography)} primary SEC EDGAR filing source(s) with "
            f"{claims_result.valid_claims} verified factual and analytical claims.",
        ]

        if can_complete:
            exec_summary_parts.append(
                "All required research questions were successfully resolved and supported by verified filing evidence."
            )
        else:
            exec_summary_parts.append(
                f"Notice: Research concluded with status {final_status.value}. Certain questions could not be fully answered: "
                + "; ".join(limitations)
            )

        executive_summary = "Executive Summary\n\n" + "\n\n".join(exec_summary_parts)

        report = FinalReport(
            report_id=f"RPT_{run.run_id[:8]}",
            run_id=run.run_id,
            company_name=itinerary.company_name,
            ticker=itinerary.ticker,
            cik=itinerary.cik,
            objective=run.objective,
            status=final_status,
            generated_at=datetime.now(timezone.utc),
            executive_summary=executive_summary,
            sections=section_drafts,
            bibliography=bibliography,
            unresolved_limitations=limitations,
            is_complete=can_complete,
            validation_passed=claims_result.is_valid,
        )

        logger.info("Stage 2 complete: assembled final report %s (status: %s)", report.report_id, final_status.value)
        return report
