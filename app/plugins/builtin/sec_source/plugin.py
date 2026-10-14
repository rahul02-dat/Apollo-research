"""Built-in SEC EDGAR Source Plugin."""

import hashlib
import logging
from typing import Any
from app.connectors.sec_edgar_client import SECEdgarClient
from app.models.sources import SourceDocumentRef, SourceQuery
from app.plugins.manifest import PluginManifest

logger = logging.getLogger(__name__)


class SECSourcePlugin:
    """Official SEC EDGAR source connector plugin."""

    def __init__(self, client: SECEdgarClient | None = None) -> None:
        self.client = client or SECEdgarClient()
        self.manifest = PluginManifest(
            plugin_id="sec_edgar",
            display_name="SEC EDGAR Public Connector",
            version="1.0.0",
            api_version="1.0",
            plugin_type="source_connector",
            capabilities=[
                "sec.issuer.resolve",
                "sec.filings.search",
                "sec.filings.fetch",
                "sec.facts.fetch",
            ],
            required_permissions=["network.outbound.sec_edgar"],
            config_schema={
                "user_agent": {"type": "string"},
                "rate_limit_per_sec": {"type": "number"},
            },
            enabled_by_default=True,
        )

    def resolve_issuer(self, identifier: str) -> dict[str, Any]:
        """Resolves ticker or company name to verified CIK."""
        return self.client.resolve_issuer(identifier)

    def search(self, query: SourceQuery) -> list[SourceDocumentRef]:
        """Discovers recent relevant filings for an issuer."""
        if not query.issuer_cik:
            raise ValueError("SourceQuery requires issuer_cik for SEC EDGAR search.")

        submissions = self.client.get_submissions(query.issuer_cik)
        recent = submissions.get("filings", {}).get("recent", {})
        if not recent:
            return []

        form_types = recent.get("form", [])
        accession_numbers = recent.get("accessionNumber", [])
        filing_dates = recent.get("filingDate", [])
        report_dates = recent.get("reportDate", [])
        primary_docs = recent.get("primaryDocument", [])
        primary_doc_descriptions = recent.get("primaryDocDescription", [])

        allowed_forms = set(query.filing_types or ["10-K", "10-Q", "8-K"])
        results: list[SourceDocumentRef] = []

        for i in range(len(form_types)):
            form = form_types[i]
            if form in allowed_forms:
                acc_num = accession_numbers[i]
                primary_doc = primary_docs[i]
                filing_date = filing_dates[i]
                report_date = report_dates[i] if i < len(report_dates) else filing_date
                doc_desc = primary_doc_descriptions[i] if i < len(primary_doc_descriptions) else form

                url = self.client.construct_document_url(
                    cik=query.issuer_cik,
                    accession_number=acc_num,
                    primary_document=primary_doc,
                )

                source_id = f"SEC_{form}_{acc_num.replace('-', '_')}"
                results.append(
                    SourceDocumentRef(
                        plugin_id=self.manifest.plugin_id,
                        source_id=source_id,
                        title=f"{submissions.get('name', 'Company')} Form {form} ({filing_date})",
                        url=url,
                        source_type="SEC_FILING",
                        form_type=form,
                        accession_number=acc_num,
                        filing_date=filing_date,
                        period_of_report=report_date,
                        metadata={
                            "cik": query.issuer_cik,
                            "entity_name": submissions.get("name"),
                            "primary_doc": primary_doc,
                            "description": doc_desc,
                        },
                    )
                )

                # Cap search results to top 10 most recent to conserve bandwidth
                if len(results) >= 10:
                    break

        return results

    def fetch(self, source: SourceDocumentRef) -> bytes:
        """Fetches raw filing content."""
        return self.client.fetch_filing_document(source.url)

    def get_company_facts(self, cik: str) -> dict[str, Any]:
        """Retrieves structured XBRL facts JSON for an issuer."""
        return self.client.get_company_facts(cik)


def create_plugin() -> SECSourcePlugin:
    return SECSourcePlugin()
