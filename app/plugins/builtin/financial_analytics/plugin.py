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
            "trends": {},
            "charts": {},
            "summary_highlights": [],
        }

        # 1. Revenue & Multi-Year Growth (YoY + CAGR)
        rev_records = facts_by_tag.get("Revenues") or facts_by_tag.get("RevenueFromContractWithCustomerExcludingAssessedTax", [])
        latest_rev: Decimal | None = None
        prior_rev: Decimal | None = None

        if rev_records:
            # Chronological series (earliest to latest)
            rev_chrono = self._extract_annual_series(rev_records)
            latest_rev = rev_records[0].value
            computed["metrics"]["latest_revenue"] = {
                "value": str(latest_rev),
                "formatted": self._format_currency(latest_rev),
                "period": rev_records[0].period_end,
                "evidence_id": rev_records[0].evidence_id,
            }

            # Prior year comparison
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

            # Multi-Year Trend & CAGR (if >= 2 periods)
            if len(rev_chrono) >= 2:
                series_data = []
                for idx, r in enumerate(rev_chrono):
                    val = r.value or Decimal("0")
                    growth_from_prior = None
                    if idx > 0 and rev_chrono[idx - 1].value and rev_chrono[idx - 1].value != 0:
                        prev_v = rev_chrono[idx - 1].value
                        g = ((val - prev_v) / abs(prev_v)) * Decimal("100")
                        growth_from_prior = float(g.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

                    p_label = r.fiscal_period or self._extract_year_label(r.period_end)
                    series_data.append({
                        "period": r.period_end or "Unknown",
                        "label": p_label,
                        "value": float(val),
                        "formatted": self._format_currency(val),
                        "yoy_growth_pct": growth_from_prior,
                        "evidence_id": r.evidence_id,
                    })

                initial_rec = rev_chrono[0]
                final_rec = rev_chrono[-1]
                n_years = self._calculate_year_span(initial_rec.period_end, final_rec.period_end, len(rev_chrono) - 1)

                cagr_val, cagr_str = self._compute_cagr(initial_rec.value or Decimal("0"), final_rec.value or Decimal("0"), n_years)

                computed["trends"]["revenue_cagr"] = {
                    "years": n_years,
                    "cagr_pct": float(cagr_val) if cagr_val is not None else None,
                    "formatted": cagr_str,
                    "start_period": initial_rec.period_end,
                    "end_period": final_rec.period_end,
                    "start_value": self._format_currency(initial_rec.value or Decimal("0")),
                    "end_value": self._format_currency(final_rec.value or Decimal("0")),
                }
                computed["trends"]["revenue_series"] = series_data

                if cagr_val is not None:
                    computed["summary_highlights"].append(
                        f"{n_years}-Year Revenue CAGR: {cagr_str} (from {self._format_currency(initial_rec.value or Decimal('0'))} in {self._extract_year_label(initial_rec.period_end)} to {self._format_currency(final_rec.value or Decimal('0'))} in {self._extract_year_label(final_rec.period_end)})"
                    )

                # Chart dataset for revenue
                computed["charts"]["revenue_trend"] = {
                    "title": f"Annual Revenue Trend ({n_years}-Year)",
                    "labels": [s["label"] for s in series_data],
                    "raw_values": [s["value"] for s in series_data],
                    "values_in_billions": [self._to_billions(s["value"]) for s in series_data],
                    "unit": "USD Billions" if any(abs(s["value"]) >= 1e9 for s in series_data) else "USD Millions",
                    "cagr_formatted": cagr_str,
                }

        # 2. Operating Income & Operating Margin Multi-Year
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

        # 3. Net Income & Net Profit Margin Multi-Year
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

        # Margin Multi-Year Series & Chart
        if rev_records:
            rev_chrono = self._extract_annual_series(rev_records)
            op_by_period = {r.period_end: r.value for r in self._extract_annual_series(op_inc_records) if r.period_end}
            net_by_period = {r.period_end: r.value for r in self._extract_annual_series(net_inc_records) if r.period_end}

            margin_series = []
            for r in rev_chrono:
                p = r.period_end or ""
                p_label = r.fiscal_period or self._extract_year_label(p)
                r_val = r.value or Decimal("0")
                if r_val > 0:
                    op_v = op_by_period.get(p)
                    net_v = net_by_period.get(p)
                    op_m = float(((op_v / r_val) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)) if op_v is not None else None
                    net_m = float(((net_v / r_val) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)) if net_v is not None else None
                    margin_series.append({
                        "period": p,
                        "label": p_label,
                        "operating_margin_pct": op_m,
                        "net_margin_pct": net_m,
                    })

            if margin_series:
                computed["trends"]["margin_series"] = margin_series
                computed["charts"]["margin_trend"] = {
                    "title": "Operating & Net Profit Margin Trajectory",
                    "labels": [m["label"] for m in margin_series],
                    "operating_margins": [m["operating_margin_pct"] for m in margin_series],
                    "net_margins": [m["net_margin_pct"] for m in margin_series],
                    "unit": "%",
                }

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

        # Balance sheet capital structure chart
        if latest_assets is not None and latest_liab is not None:
            computed["charts"]["capital_structure"] = {
                "title": "Capital Structure & Liquidity Breakdown",
                "labels": ["Total Assets", "Total Liabilities", "Cash & Equivalents"],
                "raw_values": [
                    float(latest_assets),
                    float(latest_liab),
                    float(latest_cash or Decimal("0")),
                ],
                "values_in_billions": [
                    self._to_billions(latest_assets),
                    self._to_billions(latest_liab),
                    self._to_billions(latest_cash or Decimal("0")),
                ],
                "unit": "USD Billions",
            }

        return computed

    @staticmethod
    def _to_billions(val: Any) -> float:
        if val is None:
            return 0.0
        try:
            d = Decimal(str(val)) / Decimal("1000000000")
            return float(d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        except Exception:
            return 0.0

    @classmethod
    def _extract_annual_series(cls, records: list[EvidenceRecord]) -> list[EvidenceRecord]:
        """Extracts unique annual periods sorted chronologically (earliest to latest)."""
        seen_dates: set[str] = set()
        unique_records: list[EvidenceRecord] = []
        for r in records:
            p_end = r.period_end or ""
            if p_end and p_end not in seen_dates:
                seen_dates.add(p_end)
                unique_records.append(r)
        unique_records.sort(key=lambda r: (r.period_end or "", r.period_start or ""))
        return unique_records

    @staticmethod
    def _extract_year_label(period_date: str | None) -> str:
        if not period_date:
            return "FY"
        return period_date[:4]

    @staticmethod
    def _calculate_year_span(start_date: str | None, end_date: str | None, default_span: int) -> int:
        if start_date and end_date and len(start_date) >= 4 and len(end_date) >= 4:
            try:
                s_yr = int(start_date[:4])
                e_yr = int(end_date[:4])
                span = e_yr - s_yr
                if span > 0:
                    return span
            except ValueError:
                pass
        return max(1, default_span)

    @staticmethod
    def _compute_cagr(initial_val: Decimal, final_val: Decimal, periods: int) -> tuple[Decimal | None, str]:
        """Computes Compound Annual Growth Rate over `periods` years."""
        if periods <= 0:
            return None, "N/A"
        if initial_val <= 0 or final_val <= 0:
            return None, "N/A (non-positive base)"
        try:
            ratio = float(final_val / initial_val)
            cagr_float = (ratio ** (1.0 / periods)) - 1.0
            cagr_dec = Decimal(str(cagr_float * 100.0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            sign = "+" if cagr_dec > 0 else ""
            return cagr_dec, f"{sign}{cagr_dec}%"
        except Exception as e:
            logger.warning("Error computing CAGR: %s", e)
            return None, "N/A"

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
