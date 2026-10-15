"""Athena Research Agent."""

import hashlib
import logging
from typing import Any
from app.models.evidence import EvidenceRecord
from app.models.gaps import FollowUpRequest
from app.models.research import ResearchQuestion
from app.models.sources import SourceDocument, SourceDocumentRef, SourceQuery
from app.plugins.contracts import (
    DocumentExtractor,
    EvidenceValidator,
    SourceConnector,
)
from app.plugins.registry import PluginRegistry
from app.services.evidence_registry import EvidenceRegistry

logger = logging.getLogger(__name__)


class AthenaResearchAgent:
    """Discovers and retrieves filings and facts via registered source & extractor plugins."""

    def __init__(
        self,
        registry: PluginRegistry,
        evidence_registry: EvidenceRegistry,
    ) -> None:
        self.plugin_registry = registry
        self.evidence_registry = evidence_registry

    def retrieve_initial_evidence(
        self,
        cik: str,
        questions: list[ResearchQuestion],
        source_plugin_id: str = "sec_edgar",
    ) -> list[EvidenceRecord]:
        """Discovers recent 10-K/10-Q filings and company facts, extracts and validates evidence."""
        source_plugin = self.plugin_registry.get_typed_plugin(source_plugin_id, SourceConnector)
        html_extractor = self.plugin_registry.get_typed_plugin("filing_html", DocumentExtractor)
        xbrl_extractor = self.plugin_registry.get_typed_plugin("xbrl_facts", DocumentExtractor)
        validator = self.plugin_registry.get_typed_plugin("financial_checks", EvidenceValidator)

        all_evidence: list[EvidenceRecord] = []

        # 1. Search for primary filings
        query = SourceQuery(
            query_id=f"QRY_{cik}_INIT",
            issuer_cik=cik,
            filing_types=["10-K", "10-Q"],
        )
        refs = self.plugin_registry.executor.execute(
            source_plugin,
            "sec.filings.search",
            source_plugin.search,
            query,
        )

        if not refs:
            logger.warning("No filing references returned by source plugin for CIK %s", cik)
            return []

        # Select the primary annual 10-K or latest 10-Q
        primary_ref = refs[0]
        for ref in refs:
            if ref.form_type == "10-K":
                primary_ref = ref
                break

        # Register source document
        source_doc = SourceDocument(
            source_id=primary_ref.source_id,
            issuer_cik=cik,
            accession_number=primary_ref.accession_number or "0000000000-00-000000",
            form_type=primary_ref.form_type or "10-K",
            filed_at=primary_ref.filing_date or "2024-01-01",
            period_of_report=primary_ref.period_of_report or primary_ref.filing_date or "2024-01-01",
            title=primary_ref.title,
            source_url=primary_ref.url,
            metadata=primary_ref.metadata,
        )
        self.evidence_registry.add_source(source_doc)

        # 2. Fetch filing HTML content and extract narrative evidence
        try:
            doc_bytes = self.plugin_registry.executor.execute(
                source_plugin,
                "sec.filings.fetch",
                source_plugin.fetch,
                primary_ref,
            )
            source_doc.content_sha256 = hashlib.sha256(doc_bytes).hexdigest()

            html_records = self.plugin_registry.executor.execute(
                html_extractor,
                "documents.html.extract",
                html_extractor.extract,
                doc_bytes,
                primary_ref,
                questions,
            )
            all_evidence.extend(html_records)
        except Exception as e:
            logger.error("Failed to fetch/extract narrative for source %s: %s", primary_ref.source_id, e)

        # 3. Retrieve structured XBRL Company Facts
        try:
            facts_data = self.plugin_registry.executor.execute(
                source_plugin,
                "sec.facts.fetch",
                source_plugin.get_company_facts,
                cik,
            )
            xbrl_records = self.plugin_registry.executor.execute(
                xbrl_extractor,
                "documents.xbrl.extract",
                xbrl_extractor.extract,
                facts_data,
                primary_ref,
                questions,
            )
            all_evidence.extend(xbrl_records)
        except Exception as e:
            logger.error("Failed to fetch/extract XBRL facts for CIK %s: %s", cik, e)

        # 3b. Retrieve Material Events (Form 8-K) and Insider Trading (Form 4)
        if self.plugin_registry.has_plugin("sec_material_events"):
            try:
                events_plugin = self.plugin_registry.get_plugin("sec_material_events")
                events = events_plugin.fetch_events(cik, limit=3)
                txs = events_plugin.fetch_insider_transactions(cik, limit=5)

                for evt in events:
                    evt_src = SourceDocument(
                        source_id=f"SEC_8-K_{evt.accession_number.replace('-', '_')}",
                        issuer_cik=cik,
                        accession_number=evt.accession_number,
                        form_type="8-K",
                        filed_at=evt.filing_date,
                        period_of_report=evt.report_date,
                        title=evt.title,
                        source_url=evt.source_url,
                        metadata={"description": evt.summary},
                    )
                    self.evidence_registry.add_source(evt_src)

                for tx in txs:
                    tx_src = SourceDocument(
                        source_id=f"SEC_4_{tx.accession_number.replace('-', '_')}",
                        issuer_cik=cik,
                        accession_number=tx.accession_number,
                        form_type="4",
                        filed_at=tx.filing_date,
                        period_of_report=tx.transaction_date,
                        title=f"Form 4 Insider Trading ({tx.reporting_owner_name})",
                        source_url=tx.source_url,
                        metadata={"reporting_owner": tx.reporting_owner_name, "role": tx.relationship_role},
                    )
                    self.evidence_registry.add_source(tx_src)

                event_records = events_plugin.to_evidence_records(events, txs)
                for rec in event_records:
                    if not rec.question_ids:
                        rec.question_ids = ["Q_OVERVIEW"]
                all_evidence.extend(event_records)
                logger.info("Athena registered %d Form 8-K material events and %d Form 4 insider transactions", len(events), len(txs))
            except Exception as e:
                logger.debug("Optional material events retrieval skipped: %s", e)

        # 3c. Retrieve Earnings Call Transcripts & Management Guidance
        if self.plugin_registry.has_plugin("management_transcripts"):
            try:
                transcripts_plugin = self.plugin_registry.get_plugin("management_transcripts")
                ticker = primary_ref.metadata.get("ticker") if primary_ref.metadata else None
                if not ticker:
                    ticker = primary_ref.title.split()[0] if primary_ref.title else "COMPANY"

                quotes = transcripts_plugin.fetch_transcripts(ticker, cik=cik)
                guidance = transcripts_plugin.extract_guidance(ticker, cik=cik)

                transcript_src = SourceDocument(
                    source_id="CALL_TRANSCRIPT_Q4",
                    issuer_cik=cik,
                    accession_number="TRANSCRIPT-Q4",
                    form_type="EARNINGS_CALL",
                    filed_at=primary_ref.filing_date or "2024-01-01",
                    period_of_report="Q4",
                    title=f"{ticker} Executive Earnings Call Commentary",
                    source_url=f"https://www.sec.gov/edgar/searchedgar/companysearch?CIK={cik}",
                )
                self.evidence_registry.add_source(transcript_src)

                guidance_src = SourceDocument(
                    source_id="CALL_GUIDANCE_Q4",
                    issuer_cik=cik,
                    accession_number="GUIDANCE-Q4",
                    form_type="MANAGEMENT_GUIDANCE",
                    filed_at=primary_ref.filing_date or "2024-01-01",
                    period_of_report="FY2027",
                    title=f"{ticker} Forward Management Guidance Targets",
                    source_url=f"https://www.sec.gov/edgar/searchedgar/companysearch?CIK={cik}",
                )
                self.evidence_registry.add_source(guidance_src)

                transcript_records = transcripts_plugin.to_evidence_records(quotes, guidance)
                for rec in transcript_records:
                    if not rec.question_ids:
                        rec.question_ids = ["Q_OVERVIEW"]
                all_evidence.extend(transcript_records)
                logger.info("Athena registered %d earnings transcript quotes and guidance targets", len(transcript_records))
            except Exception as e:
                logger.debug("Optional transcript retrieval skipped: %s", e)

        # 4. Validate evidence provenance and consistency
        sources_dict = {s.source_id: s for s in self.evidence_registry.list_sources()}
        validated_evidence = self.plugin_registry.executor.execute(
            validator,
            "evidence.financial.validate",
            validator.validate,
            all_evidence,
            sources_dict,
        )

        # 5. Register into repository
        self.evidence_registry.add_evidence_batch(validated_evidence)
        logger.info("Athena retrieved and registered %d evidence items for CIK %s", len(validated_evidence), cik)
        return validated_evidence

    def retrieve_followup_evidence(
        self,
        cik: str,
        follow_up: FollowUpRequest,
        target_question_id: str,
        source_plugin_id: str = "sec_edgar",
    ) -> list[EvidenceRecord]:
        """Performs targeted follow-up retrieval based on Hermes gap specification."""
        source_plugin = self.plugin_registry.get_typed_plugin(source_plugin_id, SourceConnector)
        html_extractor = self.plugin_registry.get_typed_plugin("filing_html", DocumentExtractor)
        validator = self.plugin_registry.get_typed_plugin("financial_checks", EvidenceValidator)

        logger.info("Athena executing targeted follow-up for question %s (sections: %s)", target_question_id, follow_up.target_sections)

        # Query for filings specified by Hermes
        query = SourceQuery(
            query_id=f"QRY_{cik}_FOLLOWUP",
            issuer_cik=cik,
            terms=follow_up.terms,
            filing_types=follow_up.filing_types,
        )
        refs = self.plugin_registry.executor.execute(
            source_plugin,
            "sec.filings.search",
            source_plugin.search,
            query,
        )
        if not refs:
            return []

        chosen_ref = refs[0]
        if not self.evidence_registry.get_source(chosen_ref.source_id):
            source_doc = SourceDocument(
                source_id=chosen_ref.source_id,
                issuer_cik=cik,
                accession_number=chosen_ref.accession_number or "0000000000-00-000000",
                form_type=chosen_ref.form_type or "10-K",
                filed_at=chosen_ref.filing_date or "2024-01-01",
                period_of_report=chosen_ref.period_of_report or chosen_ref.filing_date or "2024-01-01",
                title=chosen_ref.title,
                source_url=chosen_ref.url,
            )
            self.evidence_registry.add_source(source_doc)

        try:
            doc_bytes = self.plugin_registry.executor.execute(
                source_plugin,
                "sec.filings.fetch",
                source_plugin.fetch,
                chosen_ref,
            )
            extracted = self.plugin_registry.executor.execute(
                html_extractor,
                "documents.html.extract",
                html_extractor.extract,
                doc_bytes,
                chosen_ref,
                [ResearchQuestion(question_id=target_question_id, section_id="", question=f"Follow-up for {target_question_id}")],
            )

            # Link specifically to the target question
            for rec in extracted:
                if target_question_id not in rec.question_ids:
                    rec.question_ids.append(target_question_id)

            sources_dict = {s.source_id: s for s in self.evidence_registry.list_sources()}
            validated = self.plugin_registry.executor.execute(
                validator,
                "evidence.financial.validate",
                validator.validate,
                extracted,
                sources_dict,
            )
            self.evidence_registry.add_evidence_batch(validated)
            return validated
        except Exception as e:
            logger.error("Targeted follow-up retrieval failed: %s", e)
            return []
