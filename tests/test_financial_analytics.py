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


def test_multi_year_trend_analysis_and_cagr() -> None:
    plugin = FinancialAnalyticsPlugin()

    # 3-year multi-period revenue and income records: FY22, FY23, FY24
    evidence = [
        # FY22: $198.270B
        EvidenceRecord(
            evidence_id="EV_REV_2022",
            source_id="SRC_10K_2022",
            locator="XBRL us-gaap:Revenues",
            fact_name="Revenues",
            value=Decimal("198270000000"),
            unit="USD",
            period_end="2022-06-30",
            fiscal_period="FY 2022",
            validation_status=EvidenceValidationStatus.VALID,
        ),
        # FY23: $211.915B
        EvidenceRecord(
            evidence_id="EV_REV_2023",
            source_id="SRC_10K_2023",
            locator="XBRL us-gaap:Revenues",
            fact_name="Revenues",
            value=Decimal("211915000000"),
            unit="USD",
            period_end="2023-06-30",
            fiscal_period="FY 2023",
            validation_status=EvidenceValidationStatus.VALID,
        ),
        # FY24: $245.122B
        EvidenceRecord(
            evidence_id="EV_REV_2024",
            source_id="SRC_10K_2024",
            locator="XBRL us-gaap:Revenues",
            fact_name="Revenues",
            value=Decimal("245122000000"),
            unit="USD",
            period_end="2024-06-30",
            fiscal_period="FY 2024",
            validation_status=EvidenceValidationStatus.VALID,
        ),
        # Operating income FY22: $83.383B (42.06% margin)
        EvidenceRecord(
            evidence_id="EV_OP_INC_2022",
            source_id="SRC_10K_2022",
            locator="XBRL us-gaap:OperatingIncomeLoss",
            fact_name="OperatingIncomeLoss",
            value=Decimal("83383000000"),
            unit="USD",
            period_end="2022-06-30",
            fiscal_period="FY 2022",
            validation_status=EvidenceValidationStatus.VALID,
        ),
        # Operating income FY24: $109.433B (44.64% margin)
        EvidenceRecord(
            evidence_id="EV_OP_INC_2024",
            source_id="SRC_10K_2024",
            locator="XBRL us-gaap:OperatingIncomeLoss",
            fact_name="OperatingIncomeLoss",
            value=Decimal("109433000000"),
            unit="USD",
            period_end="2024-06-30",
            fiscal_period="FY 2024",
            validation_status=EvidenceValidationStatus.VALID,
        ),
        # Balance sheet items for capital structure chart
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
        EvidenceRecord(
            evidence_id="EV_CASH_2024",
            source_id="SRC_10K_2024",
            locator="XBRL us-gaap:CashAndCashEquivalentsAtCarryingValue",
            fact_name="CashAndCashEquivalentsAtCarryingValue",
            value=Decimal("75535000000"),
            unit="USD",
            period_end="2024-06-30",
            validation_status=EvidenceValidationStatus.VALID,
        ),
    ]

    results = plugin.compute_metrics(evidence)

    # 1. Trends structure
    assert "trends" in results
    assert "revenue_cagr" in results["trends"]
    assert "revenue_series" in results["trends"]
    assert len(results["trends"]["revenue_series"]) == 3

    # CAGR: (245.122 / 198.270) ** (1 / 2) - 1 = 11.19%
    cagr_info = results["trends"]["revenue_cagr"]
    assert cagr_info["years"] == 2
    assert cagr_info["cagr_pct"] == 11.19
    assert cagr_info["formatted"] == "+11.19%"
    assert cagr_info["start_value"] == "$198.27B"
    assert cagr_info["end_value"] == "$245.12B"

    # 2. Charts structure for PDF and Frontend
    assert "charts" in results
    rev_chart = results["charts"]["revenue_trend"]
    assert rev_chart["labels"] == ["FY 2022", "FY 2023", "FY 2024"]
    assert rev_chart["values_in_billions"] == [198.27, 211.92, 245.12]
    assert rev_chart["unit"] == "USD Billions"
    assert rev_chart["cagr_formatted"] == "+11.19%"

    margin_chart = results["charts"]["margin_trend"]
    assert len(margin_chart["labels"]) == 3
    assert margin_chart["operating_margins"][0] == 42.06  # FY22
    assert margin_chart["operating_margins"][2] == 44.64  # FY24

    cap_chart = results["charts"]["capital_structure"]
    assert cap_chart["labels"] == ["Total Assets", "Total Liabilities", "Cash & Equivalents"]
    assert cap_chart["values_in_billions"] == [512.16, 243.69, 75.54]

    # Non-positive base handling
    cagr_zero, str_zero = plugin._compute_cagr(Decimal("0"), Decimal("100"), 3)
    assert cagr_zero is None
    assert "non-positive" in str_zero

