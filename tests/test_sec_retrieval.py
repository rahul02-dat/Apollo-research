"""Acceptance Test AT-02: Primary-Source Retrieval and Evidence Normalization."""

from typing import Any
import pytest
from app.agents.athena import AthenaResearchAgent
from app.models.research import ResearchQuestion
from app.plugins.registry import PluginRegistry
from app.services.evidence_registry import EvidenceRegistry


def test_at02_primary_source_retrieval(
    plugin_registry: PluginRegistry,
    evidence_registry: EvidenceRegistry,
    fake_source: Any,
) -> None:
    plugin_registry.register(fake_source, overwrite=True)
    athena = AthenaResearchAgent(plugin_registry, evidence_registry)

    questions = [
        ResearchQuestion(
            question_id="Q_REV",
            section_id="SEC_PERF",
            question="What was Microsoft's revenue?",
        ),
        ResearchQuestion(
            question_id="Q_RISK",
            section_id="SEC_RISK",
            question="What are the principal risk factors?",
        ),
    ]

    records = athena.retrieve_initial_evidence(
        cik="0000789019",
        questions=questions,
        source_plugin_id="fake_source",
    )

    assert len(records) > 0

    # Verify source document is stored in registry with canonical SEC link
    sources = evidence_registry.list_sources()
    assert len(sources) >= 1
    src = sources[0]
    assert src.form_type == "10-K"
    assert "https://www.sec.gov/Archives/edgar/data" in src.source_url
    assert src.accession_number == "0000789019-24-000078"

    # Verify extracted XBRL facts
    xbrl_facts = [r for r in records if "XBRL" in r.evidence_id]
    assert len(xbrl_facts) > 0
    rev_fact = next((f for f in xbrl_facts if f.fact_name == "Revenues"), None)
    assert rev_fact is not None
    assert rev_fact.value == 245122000000
    assert rev_fact.unit == "USD"
    assert rev_fact.period_end == "2024-06-30"

    # Verify extracted narrative records
    html_records = [r for r in records if "HTML" in r.evidence_id]
    assert len(html_records) > 0
    risk_rec = next((r for r in html_records if "risk" in r.locator.lower()), None)
    assert risk_rec is not None
    assert "Risk Factors" in risk_rec.locator
    assert len(risk_rec.excerpt) > 50
