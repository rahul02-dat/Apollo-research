"""Built-in HTML Filing Narrative Extractor Plugin."""

import logging
import re
from bs4 import BeautifulSoup
from app.models.evidence import EvidenceRecord, EvidenceValidationStatus
from app.models.research import ResearchQuestion
from app.models.sources import SourceDocumentRef
from app.plugins.manifest import PluginManifest

logger = logging.getLogger(__name__)


class HTMLExtractorPlugin:
    """Extracts narrative sections and disclosures from SEC filing HTML."""

    def __init__(self) -> None:
        self.manifest = PluginManifest(
            plugin_id="filing_html",
            display_name="SEC Filing HTML Narrative Extractor",
            version="1.0.0",
            api_version="1.0",
            plugin_type="document_extractor",
            capabilities=["documents.html.extract"],
            required_permissions=[],
            config_schema={},
            enabled_by_default=True,
        )

        # Standard SEC Item patterns
        self.section_patterns = [
            ("Item 1A. Risk Factors", re.compile(r"Item\s+1A[\.\:\s\-]+Risk\s+Factors", re.IGNORECASE)),
            ("Item 7. Management's Discussion and Analysis", re.compile(r"Item\s+7[\.\:\s\-]+Management['’]s\s+Discussion", re.IGNORECASE)),
            ("Item 7A. Quantitative and Qualitative Disclosures", re.compile(r"Item\s+7A[\.\:\s\-]+Quantitative", re.IGNORECASE)),
            ("Item 1. Business", re.compile(r"Item\s+1[\.\:\s\-]+Business", re.IGNORECASE)),
            ("Segment Information", re.compile(r"Segment\s+(Information|Reporting|Results)", re.IGNORECASE)),
            ("Liquidity and Capital Resources", re.compile(r"Liquidity\s+and\s+Capital\s+Resources", re.IGNORECASE)),
        ]

    def extract(
        self,
        content: bytes | str,
        document_ref: SourceDocumentRef,
        questions: list[ResearchQuestion] | None = None,
    ) -> list[EvidenceRecord]:
        """Extracts narrative evidence records from HTML filing text."""
        raw_text = content.decode("utf-8", errors="replace") if isinstance(content, bytes) else content

        soup = BeautifulSoup(raw_text, "html.parser")
        # Extract text while removing script/style tags
        for element in soup(["script", "style"]):
            element.decompose()

        full_text = soup.get_text(separator="\n")
        # Normalize whitespace
        lines = [line.strip() for line in full_text.splitlines() if line.strip()]
        clean_text = "\n".join(lines)

        evidence_records: list[EvidenceRecord] = []
        found_sections: set[str] = set()

        # Search for key sections
        for section_name, pattern in self.section_patterns:
            matches = list(pattern.finditer(clean_text))
            if not matches:
                continue

            # Pick the most substantial occurrence (often the body, after Table of Contents)
            chosen_match = None
            for m in matches:
                # TOC matches often have page numbers or dots right after
                sub = clean_text[m.start():m.start() + 400]
                if "...." not in sub:
                    chosen_match = m
                    break
            if not chosen_match:
                chosen_match = matches[-1]

            start_idx = chosen_match.start()
            # Extract excerpt of reasonable length (up to 3000 chars)
            excerpt_candidate = clean_text[start_idx:start_idx + 2500].strip()

            if len(excerpt_candidate) > 100:
                found_sections.add(section_name)
                section_slug = re.sub(r"[^a-zA-Z0-9]+", "_", section_name).strip("_").lower()
                evidence_id = f"EV_HTML_{document_ref.source_id}_{section_slug}"

                # Link to relevant questions based on keywords
                matched_qids: list[str] = []
                if questions:
                    for q in questions:
                        q_text = q.question.lower()
                        if any(term in q_text for term in ["risk", "uncertaint"]) and "risk" in section_slug:
                            matched_qids.append(q.question_id)
                        elif any(term in q_text for term in ["segment", "division"]) and "segment" in section_slug:
                            matched_qids.append(q.question_id)
                        elif any(term in q_text for term in ["liquidity", "debt", "cash flow"]) and "liquidity" in section_slug:
                            matched_qids.append(q.question_id)
                        elif any(term in q_text for term in ["management", "m&a", "operation", "performance"]) and "management" in section_slug:
                            matched_qids.append(q.question_id)
                        elif any(term in q_text for term in ["business", "overview"]) and "business" in section_slug:
                            matched_qids.append(q.question_id)

                evidence_records.append(
                    EvidenceRecord(
                        evidence_id=evidence_id,
                        source_id=document_ref.source_id,
                        source_url=document_ref.url,
                        locator=section_name,
                        excerpt=excerpt_candidate,
                        question_ids=matched_qids,
                        period_start=document_ref.period_of_report,
                        period_end=document_ref.period_of_report,
                        fiscal_period=document_ref.form_type,
                        validation_status=EvidenceValidationStatus.VALID,
                        metadata={
                            "section_name": section_name,
                            "form_type": document_ref.form_type,
                        },
                    )
                )

        # Fallback: if no specific sections were matched by regex, capture general narrative passage
        if not evidence_records and len(clean_text) > 200:
            evidence_records.append(
                EvidenceRecord(
                    evidence_id=f"EV_HTML_{document_ref.source_id}_overview",
                    source_id=document_ref.source_id,
                    source_url=document_ref.url,
                    locator="General Filing Disclosure",
                    excerpt=clean_text[:2000].strip(),
                    question_ids=[q.question_id for q in (questions or [])[:1]],
                    period_start=document_ref.period_of_report,
                    period_end=document_ref.period_of_report,
                    fiscal_period=document_ref.form_type,
                    validation_status=EvidenceValidationStatus.VALID,
                )
            )

        return evidence_records


def create_plugin() -> HTMLExtractorPlugin:
    return HTMLExtractorPlugin()
