"""Built-in Financial Analytics Plugin for ratio computations and multi-period metrics."""

from decimal import Decimal, ROUND_HALF_UP
import logging
from typing import Any
from app.models.evidence import EvidenceRecord
from app.plugins.manifest import PluginManifest

logger = logging.getLogger(__name__)


class FinancialAnalyticsPlugin:
    """Computes deterministic financial ratios, growth rates, and margins from evidence records."""

    def __init__(self) -> None:
        self.manifest = PluginManifest(
            plugin_id="financial_analytics",
            display_name="Deterministic Financial Analytics & Ratio Engine",
            version="1.0.0",
            api_version="1.0",
            plugin_type="financial_analytics",
            capabilities=["financial.metrics.compute"],
            required_permissions=[],
            config_schema={},
            enabled_by_default=True,
        )

    def compute_metrics(self, evidence: list[EvidenceRecord]) -> dict[str, Any]:
        """Analyzes numeric evidence records and calculates standard financial ratios."""
        facts_by_tag: dict[str, list[EvidenceRecord]] = {}

        for rec in evidence:
            if rec.fact_name and rec.value is not None:
                tag = rec.fact_name
                if tag not in facts_by_tag:
                    facts_by_tag[tag] = []
                facts_by_tag[tag].append(rec)

        # Sort each tag's entries by period_end descending
        for tag in facts_by_tag:
            facts_by_tag[tag].sort(key=lambda r: (r.period_end or "", r.period_start or ""), reverse=True)

        computed: dict[str, Any] = {
            "metrics": {},
            "ratios": {},
            "summary_highlights": [],
        }

        # 1. Revenue & Growth
        rev_records = facts_by_tag.get("Revenues") or facts_by_tag.get("RevenueFromContractWithCustomerExcludingAssessedTax", [])
        latest_rev: Decimal | None = None
        prior_rev: Decimal | None = None

        if rev_records:
            latest_rev = rev_records[0].value
            computed["metrics"]["latest_revenue"] = {
                "value": str(latest_rev),
                "formatted": self._format_currency(latest_rev),
                "period": rev_records[0].period_end,
                "evidence_id": rev_records[0].evidence_id,
            }
            if len(rev_records) > 1:
                prior_rev = rev_records[1].value
                computed["metrics"]["prior_revenue"] = {
                    "value": str(prior_rev),
                    "formatted": self._format_currency(prior_rev),
                    "period": rev_records[1].period_end,
                    "evidence_id": rev_records[1].evidence_id,
                }
                if prior_rev and prior_rev != 0:
                    yoy_growth = ((latest_rev - prior_rev) / abs(prior_rev)) * Decimal("100")
                    yoy_growth_rounded = yoy_growth.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    sign = "+" if yoy_growth > 0 else ""
                    computed["ratios"]["revenue_yoy_growth"] = {
                        "value": float(yoy_growth_rounded),
                        "formatted": f"{sign}{yoy_growth_rounded}%",
                    }
                    computed["summary_highlights"].append(
                        f"YoY Revenue Growth: {sign}{yoy_growth_rounded}% (from {self._format_currency(prior_rev)} to {self._format_currency(latest_rev)})"
                    )

        # 2. Operating Income & Operating Margin
        op_inc_records = facts_by_tag.get("OperatingIncomeLoss", [])
        if op_inc_records:
            latest_op_inc = op_inc_records[0].value
            computed["metrics"]["operating_income"] = {
                "value": str(latest_op_inc),
                "formatted": self._format_currency(latest_op_inc),
                "period": op_inc_records[0].period_end,
                "evidence_id": op_inc_records[0].evidence_id,
            }
            if latest_rev and latest_rev > 0 and latest_op_inc is not None:
                op_margin = (latest_op_inc / latest_rev) * Decimal("100")
                op_margin_rounded = op_margin.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                computed["ratios"]["operating_margin"] = {
                    "value": float(op_margin_rounded),
                    "formatted": f"{op_margin_rounded}%",
                }
                computed["summary_highlights"].append(f"Operating Margin: {op_margin_rounded}%")

        # 3. Net Income & Net Profit Margin
        net_inc_records = facts_by_tag.get("NetIncomeLoss", [])
        if net_inc_records:
            latest_net_inc = net_inc_records[0].value
            computed["metrics"]["net_income"] = {
                "value": str(latest_net_inc),
                "formatted": self._format_currency(latest_net_inc),
                "period": net_inc_records[0].period_end,
                "evidence_id": net_inc_records[0].evidence_id,
            }
            if latest_rev and latest_rev > 0 and latest_net_inc is not None:
                net_margin = (latest_net_inc / latest_rev) * Decimal("100")
                net_margin_rounded = net_margin.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                computed["ratios"]["net_profit_margin"] = {
                    "value": float(net_margin_rounded),
                    "formatted": f"{net_margin_rounded}%",
                }
                computed["summary_highlights"].append(f"Net Profit Margin: {net_margin_rounded}%")

        # 4. Balance Sheet: Assets, Liabilities, and Cash
        assets_records = facts_by_tag.get("Assets", [])
        liab_records = facts_by_tag.get("Liabilities", [])
        cash_records = facts_by_tag.get("CashAndCashEquivalentsAtCarryingValue", [])

        latest_assets = assets_records[0].value if assets_records else None
        latest_liab = liab_records[0].value if liab_records else None
        latest_cash = cash_records[0].value if cash_records else None

        if latest_assets is not None:
            computed["metrics"]["total_assets"] = {
                "value": str(latest_assets),
                "formatted": self._format_currency(latest_assets),
            }
        if latest_liab is not None:
            computed["metrics"]["total_liabilities"] = {
                "value": str(latest_liab),
                "formatted": self._format_currency(latest_liab),
            }
        if latest_cash is not None:
            computed["metrics"]["cash_and_equivalents"] = {
                "value": str(latest_cash),
                "formatted": self._format_currency(latest_cash),
            }

        # Leverage & Solvency Ratios
        if latest_assets and latest_assets > 0 and latest_liab is not None:
            debt_to_assets = (latest_liab / latest_assets) * Decimal("100")
            debt_to_assets_rounded = debt_to_assets.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            computed["ratios"]["debt_to_assets"] = {
                "value": float(debt_to_assets_rounded),
                "formatted": f"{debt_to_assets_rounded}%",
            }
            computed["summary_highlights"].append(f"Debt-to-Assets Ratio: {debt_to_assets_rounded}%")

        if latest_liab and latest_liab > 0 and latest_cash is not None:
            cash_coverage = (latest_cash / latest_liab).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            computed["ratios"]["cash_to_liabilities"] = {
                "value": float(cash_coverage),
                "formatted": f"{cash_coverage}x",
            }

        return computed

    @staticmethod
    def _format_currency(val: Decimal) -> str:
        abs_val = abs(val)
        sign = "-" if val < 0 else ""
        if abs_val >= Decimal("1000000000"):
            return f"{sign}${abs_val / Decimal('1000000000'):.2f}B"
        if abs_val >= Decimal("1000000"):
            return f"{sign}${abs_val / Decimal('1000000'):.2f}M"
        return f"{sign}${abs_val:,.2f}"


def create_plugin() -> FinancialAnalyticsPlugin:
    return FinancialAnalyticsPlugin()
