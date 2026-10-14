"""Unit tests for Financial Analytics Plugin."""

from decimal import Decimal
import pytest
from app.models.evidence import EvidenceRecord, EvidenceValidationStatus
from app.plugins.builtin.financial_analytics.plugin import FinancialAnalyticsPlugin


def test_financial_analytics_computations() -> None:
    plugin = FinancialAnalyticsPlugin()

    evidence = [
        # Latest 2024 Revenue: $245.122B
        EvidenceRecord(
            evidence_id="EV_REV_2024",
            source_id="SRC_10K_2024",
            locator="XBRL us-gaap:Revenues",
            fact_name="Revenues",
            value=Decimal("245122000000"),
            unit="USD",
            period_start="2023-07-01",
            period_end="2024-06-30",
            fiscal_period="FY 2024",
            validation_status=EvidenceValidationStatus.VALID,
        ),
        # Prior 2023 Revenue: $211.915B
        EvidenceRecord(
            evidence_id="EV_REV_2023",
            source_id="SRC_10K_2023",
            locator="XBRL us-gaap:Revenues",
            fact_name="Revenues",
            value=Decimal("211915000000"),
            unit="USD",
            period_start="2022-07-01",
            period_end="2023-06-30",
            fiscal_period="FY 2023",
            validation_status=EvidenceValidationStatus.VALID,
        ),
        # Latest Operating Income: $109.433B
        EvidenceRecord(
            evidence_id="EV_OP_INC_2024",
            source_id="SRC_10K_2024",
            locator="XBRL us-gaap:OperatingIncomeLoss",
            fact_name="OperatingIncomeLoss",
            value=Decimal("109433000000"),
            unit="USD",
            period_start="2023-07-01",
            period_end="2024-06-30",
            fiscal_period="FY 2024",
            validation_status=EvidenceValidationStatus.VALID,
        ),
        # Latest Net Income: $88.136B
        EvidenceRecord(
            evidence_id="EV_NET_INC_2024",
            source_id="SRC_10K_2024",
            locator="XBRL us-gaap:NetIncomeLoss",
            fact_name="NetIncomeLoss",
            value=Decimal("88136000000"),
            unit="USD",
            period_start="2023-07-01",
            period_end="2024-06-30",
            fiscal_period="FY 2024",
            validation_status=EvidenceValidationStatus.VALID,
        ),
        # Total Assets: $512.163B
        EvidenceRecord(
            evidence_id="EV_ASSETS_2024",
            source_id="SRC_10K_2024",
            locator="XBRL us-gaap:Assets",
            fact_name="Assets",
            value=Decimal("512163000000"),
            unit="USD",
            period_end="2024-06-30",
            validation_status=EvidenceValidationStatus.VALID,
        ),
        # Total Liabilities: $243.686B
        EvidenceRecord(
            evidence_id="EV_LIAB_2024",
            source_id="SRC_10K_2024",
            locator="XBRL us-gaap:Liabilities",
            fact_name="Liabilities",
            value=Decimal("243686000000"),
            unit="USD",
            period_end="2024-06-30",
            validation_status=EvidenceValidationStatus.VALID,
        ),
    ]

    results = plugin.compute_metrics(evidence)

    assert "metrics" in results
    assert "ratios" in results
    assert len(results["summary_highlights"]) >= 3

    # YoY Revenue Growth: ((245.122 - 211.915) / 211.915) * 100 = 15.67%
    growth = results["ratios"]["revenue_yoy_growth"]
    assert growth["formatted"] == "+15.67%"
    assert growth["value"] == 15.67

    # Operating Margin: (109.433 / 245.122) * 100 = 44.64%
    op_margin = results["ratios"]["operating_margin"]
    assert op_margin["formatted"] == "44.64%"

    # Net Margin: (88.136 / 245.122) * 100 = 35.96%
    net_margin = results["ratios"]["net_profit_margin"]
    assert net_margin["formatted"] == "35.96%"

    # Debt-to-Assets: (243.686 / 512.163) * 100 = 47.58%
    debt_assets = results["ratios"]["debt_to_assets"]
    assert debt_assets["formatted"] == "47.58%"
