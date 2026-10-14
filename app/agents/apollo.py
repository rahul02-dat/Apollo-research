"""Apollo Orchestrator Agent."""

import logging
from typing import Any
from app.models.research import (
    QuestionStatus,
    ResearchItinerary,
    ResearchQuestion,
    ResearchRun,
    RunStatus,
    SectionDefinition,
)
from app.plugins.contracts import SourceConnector
from app.plugins.registry import PluginRegistry

logger = logging.getLogger(__name__)


class ApolloOrchestrator:
    """Plans research, controls workflow execution, manages approvals, and enforces completion invariants."""

    def __init__(self, registry: PluginRegistry) -> None:
        self.registry = registry

    def normalize_request(self, run: ResearchRun) -> ResearchRun:
        """Normalizes user query and extracts ticker or company name."""
        ticker = run.ticker
        if not ticker and run.company_name:
            words = run.company_name.strip().split()
            if len(words) == 1 and words[0].isupper() and len(words[0]) <= 5:
                ticker = words[0]

        return run.model_copy(
            update={
                "ticker": ticker,
                "status": RunStatus.PLANNING,
            }
        )

    def resolve_issuer(self, run: ResearchRun, source_plugin: SourceConnector) -> ResearchRun:
        """Resolves ticker or company name to verified CIK using the source plugin."""
        identifier = run.ticker or run.company_name
        resolved = source_plugin.resolve_issuer(identifier)

        cik = resolved.get("cik")
        official_title = resolved.get("title", run.company_name)
        ticker = resolved.get("ticker", run.ticker)

        logger.info("Resolved issuer '%s' -> CIK: %s (%s)", identifier, cik, official_title)
        return run.model_copy(
            update={
                "cik": cik,
                "company_name": official_title,
                "ticker": ticker,
            }
        )

    def plan_research(self, run: ResearchRun) -> ResearchItinerary:
        """Builds a comprehensive research itinerary with sections and questions."""
        sections = [
            SectionDefinition(
                section_id="SEC_EXEC",
                title="Executive Overview",
                description="Core operational highlights and business developments.",
                question_ids=["Q_OVERVIEW"],
            ),
            SectionDefinition(
                section_id="SEC_PERF",
                title="Financial Performance & Revenue",
                description="Analysis of top-line revenue, net income, margins, and growth.",
                question_ids=["Q_REVENUE", "Q_NET_INCOME"],
            ),
            SectionDefinition(
                section_id="SEC_LIQ",
                title="Balance Sheet, Liquidity & Debt",
                description="Examination of cash reserves, total liabilities, and debt profile.",
                question_ids=["Q_LIQUIDITY", "Q_DEBT"],
            ),
            SectionDefinition(
                section_id="SEC_SEG",
                title="Segment Performance",
                description="Breakdown of financial performance by reportable business segment.",
                question_ids=["Q_SEGMENTS"],
            ),
            SectionDefinition(
                section_id="SEC_RISK",
                title="Risks & Uncertainties",
                description="Principal regulatory, macroeconomic, and operational risk factors.",
                question_ids=["Q_RISKS"],
            ),
        ]

        questions = [
            ResearchQuestion(
                question_id="Q_OVERVIEW",
                section_id="SEC_EXEC",
                question=f"What are the principal business activities and key developments for {run.company_name}?",
                expected_evidence=["Item 1 Business", "General narrative overview"],
            ),
            ResearchQuestion(
                question_id="Q_REVENUE",
                section_id="SEC_PERF",
                question=f"What was {run.company_name}'s total revenue for the latest fiscal period and how did it change?",
                expected_evidence=["Total Revenue", "Revenues XBRL fact"],
            ),
            ResearchQuestion(
                question_id="Q_NET_INCOME",
                section_id="SEC_PERF",
                question=f"What was {run.company_name}'s net income and profitability for the latest period?",
                expected_evidence=["NetIncomeLoss", "OperatingIncomeLoss"],
            ),
            ResearchQuestion(
                question_id="Q_LIQUIDITY",
                section_id="SEC_LIQ",
                question=f"What is {run.company_name}'s cash and liquidity position?",
                expected_evidence=["CashAndCashEquivalents", "Liquidity discussion"],
            ),
            ResearchQuestion(
                question_id="Q_DEBT",
                section_id="SEC_LIQ",
                question=f"What are {run.company_name}'s total liabilities and debt obligations?",
                expected_evidence=["Liabilities", "LongTermDebt"],
            ),
            ResearchQuestion(
                question_id="Q_SEGMENTS",
                section_id="SEC_SEG",
                question=f"How did {run.company_name}'s reportable business segments perform?",
                expected_evidence=["Segment Information footnote or MD&A segment breakdown"],
            ),
            ResearchQuestion(
                question_id="Q_RISKS",
                section_id="SEC_RISK",
                question=f"What are the primary risk factors disclosed by {run.company_name}?",
                expected_evidence=["Item 1A Risk Factors disclosures"],
            ),
        ]

        itinerary = ResearchItinerary(
            itinerary_id=f"ITIN_{run.run_id[:8]}",
            run_id=run.run_id,
            company_name=run.company_name,
            ticker=run.ticker or "N/A",
            cik=run.cik or "N/A",
            sections=sections,
            questions=questions,
        )

        logger.info("Planned research itinerary with %d sections and %d questions", len(sections), len(questions))
        return itinerary
