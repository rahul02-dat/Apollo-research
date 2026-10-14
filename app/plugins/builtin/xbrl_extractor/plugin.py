"""Built-in SEC XBRL Structured Financial Facts Extractor Plugin."""

import json
import logging
from decimal import Decimal
from typing import Any
from app.models.evidence import EvidenceRecord, EvidenceValidationStatus
from app.models.research import ResearchQuestion
from app.models.sources import SourceDocumentRef
from app.plugins.manifest import PluginManifest

logger = logging.getLogger(__name__)


class XBRLExtractorPlugin:
    """Extracts structured financial facts from SEC Company Facts JSON."""

    def __init__(self) -> None:
        self.manifest = PluginManifest(
            plugin_id="xbrl_facts",
            display_name="SEC XBRL Financial Facts Extractor",
            version="1.0.0",
            api_version="1.0",
            plugin_type="document_extractor",
            capabilities=["documents.xbrl.extract"],
            required_permissions=[],
            config_schema={},
            enabled_by_default=True,
        )

        # Standard US-GAAP metrics to extract
        self.key_metrics = {
            "Revenues": "Total Revenue",
            "RevenueFromContractWithCustomerExcludingAssessedTax": "Revenue from Contracts",
            "NetIncomeLoss": "Net Income",
            "OperatingIncomeLoss": "Operating Income",
            "GrossProfit": "Gross Profit",
            "Assets": "Total Assets",
            "Liabilities": "Total Liabilities",
            "StockholdersEquity": "Stockholders' Equity",
            "CashAndCashEquivalentsAtCarryingValue": "Cash and Cash Equivalents",
            "LongTermDebtNoncurrent": "Long-Term Debt",
            "EarningsPerShareDiluted": "Diluted Earnings Per Share",
        }

    def extract(
        self,
        content: bytes | str | dict[str, Any],
        document_ref: SourceDocumentRef,
        questions: list[ResearchQuestion] | None = None,
    ) -> list[EvidenceRecord]:
        """Extracts structured numeric evidence records from SEC XBRL facts JSON."""
        if isinstance(content, (bytes, str)):
            text = content.decode("utf-8") if isinstance(content, bytes) else content
            data = json.loads(text)
        else:
            data = content

        facts = data.get("facts", {})
        us_gaap = facts.get("us-gaap", {})
        if not us_gaap:
            return []

        evidence_records: list[EvidenceRecord] = []

        for tag, label in self.key_metrics.items():
            if tag not in us_gaap:
                continue

            tag_data = us_gaap[tag]
            units_dict = tag_data.get("units", {})

            for unit, entries in units_dict.items():
                if not isinstance(entries, list) or not entries:
                    continue

                # Sort by end date descending (most recent first)
                sorted_entries = sorted(
                    entries,
                    key=lambda x: (x.get("end", ""), x.get("filed", "")),
                    reverse=True,
                )

                # Prioritize annual 10-K or recent 10-Q entries
                for entry in sorted_entries[:4]:
                    val = entry.get("val")
                    if val is None:
                        continue

                    end_date = entry.get("end", "")
                    start_date = entry.get("start", end_date)
                    fy = entry.get("fy", "")
                    fp = entry.get("fp", "")
                    fiscal_period = f"{fp} {fy}".strip() if fy else fp
                    accn = entry.get("accn", "")
                    form = entry.get("form", "10-K")

                    evidence_id = f"EV_XBRL_{tag}_{end_date}_{fp}_{fy}".replace(" ", "_")

                    # Map to relevant questions
                    matched_qids: list[str] = []
                    if questions:
                        for q in questions:
                            q_text = q.question.lower()
                            if any(k in q_text for k in ["revenue", "sales", "top-line"]) and "Revenue" in tag:
                                matched_qids.append(q.question_id)
                            elif any(k in q_text for k in ["income", "profit", "margin"]) and any(k in tag for k in ["Income", "Profit"]):
                                matched_qids.append(q.question_id)
                            elif any(k in q_text for k in ["balance sheet", "asset", "liabilit", "debt", "equity"]) and any(k in tag for k in ["Assets", "Liabilities", "Debt", "Equity"]):
                                matched_qids.append(q.question_id)
                            elif any(k in q_text for k in ["liquidity", "cash"]) and "Cash" in tag:
                                matched_qids.append(q.question_id)
                            elif any(k in q_text for k in ["performance", "results"]):
                                matched_qids.append(q.question_id)

                    source_id = document_ref.source_id
                    # Format human readable excerpt
                    val_decimal = Decimal(str(val))
                    if unit == "USD":
                        if abs(val_decimal) >= 1_000_000_000:
                            human_val = f"${val_decimal / 1_000_000_000:.2f} billion"
                        elif abs(val_decimal) >= 1_000_000:
                            human_val = f"${val_decimal / 1_000_000:.2f} million"
                        else:
                            human_val = f"${val_decimal:,.2f}"
                    else:
                        human_val = f"{val_decimal:,} {unit}"

                    excerpt = f"Reported {label} ({tag}) of {human_val} for fiscal period {fiscal_period} ending {end_date} (Form {form}, accession {accn})."

                    evidence_records.append(
                        EvidenceRecord(
                            evidence_id=evidence_id,
                            source_id=source_id,
                            locator=f"XBRL us-gaap:{tag}",
                            excerpt=excerpt,
                            question_ids=matched_qids,
                            fact_name=tag,
                            value=val_decimal,
                            unit=unit,
                            period_start=start_date,
                            period_end=end_date,
                            fiscal_period=fiscal_period,
                            validation_status=EvidenceValidationStatus.VALID,
                            metadata={
                                "accession_number": accn,
                                "form": form,
                                "metric_label": label,
                            },
                        )
                    )

        return evidence_records


def create_plugin() -> XBRLExtractorPlugin:
    return XBRLExtractorPlugin()
