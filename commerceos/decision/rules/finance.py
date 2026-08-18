"""Deterministic decision rules: finance / operations."""

from typing import Any, Dict, List, Optional

from commerceos.decision.constants import DecisionCategory, DecisionConfidence, DecisionSeverity, EvidenceSource
from commerceos.decision.recommendation import Recommendation


class FinanceRules:
    """Rules for finance and operations decisions."""

    IDLE_CASH_THRESHOLD = 10_000_000
    REFUND_RATE_THRESHOLD = 0.05
    REVENUE_DROP_THRESHOLD = 0.20

    def evaluate(
        self,
        insights: List[Dict[str, Any]],
        kpis: Dict[str, Any],
        state: Optional[Dict[str, Any]] = None,
    ) -> List[Recommendation]:
        recommendations = []
        recommendations.extend(self._idle_cash(insights, kpis, state))
        recommendations.extend(self._high_refund_rate(insights, kpis, state))
        recommendations.extend(self._revenue_falling(insights, kpis, state))
        return recommendations

    def _idle_cash(
        self,
        insights: List[Dict[str, Any]],
        kpis: Dict[str, Any],
        state: Optional[Dict[str, Any]] = None,
    ) -> List[Recommendation]:
        recommendations = []
        cash = kpis.get("cash_balance")
        if cash is None or cash < self.IDLE_CASH_THRESHOLD:
            return recommendations

        recommendations.append(
            Recommendation(
                category=DecisionCategory.FINANCE.value,
                severity=DecisionSeverity.NOTICE.value,
                title=f"Consider deploying idle cash ({cash:,.0f})",
                description=f"Cash balance is {cash:,.0f}, above the idle threshold.",
                rationale="Excess idle cash loses value to inflation. Paying down high-interest debt is a low-risk return.",
                recommended_action="Review debt obligations and consider early repayment for high-interest balances.",
                expected_impact={
                    "expected_revenue_change": 0.0,
                    "expected_profit_change": 0.02,
                    "expected_cash_change": -1.0,
                    "explanation": "Debt repayment reduces cash balance but improves net profitability.",
                },
                confidence=DecisionConfidence.HIGH.value,
                evidence=[
                    {
                        "source_type": EvidenceSource.KPI.value,
                        "source_id": "cash_balance",
                        "description": f"Cash balance = {cash:,.0f}",
                    }
                ],
            )
        )
        return recommendations

    def _high_refund_rate(
        self,
        insights: List[Dict[str, Any]],
        kpis: Dict[str, Any],
        state: Optional[Dict[str, Any]] = None,
    ) -> List[Recommendation]:
        recommendations = []
        refund_rate = kpis.get("refund_rate")
        if refund_rate is None or refund_rate < self.REFUND_RATE_THRESHOLD:
            return recommendations

        recommendations.append(
            Recommendation(
                category=DecisionCategory.OPERATIONS.value,
                severity=DecisionSeverity.HIGH.value,
                title=f"Investigate high refund rate ({refund_rate * 100:.1f}%)",
                description=f"Refund rate is {refund_rate * 100:.1f}%, above the {self.REFUND_RATE_THRESHOLD * 100:.0f}% threshold.",
                rationale="High refunds damage profit and reputation. The cause is usually product quality, description mismatch, or fulfillment issues.",
                recommended_action="Review listings, product photos, and return reasons; inspect affected SKUs.",
                expected_impact={
                    "expected_revenue_change": 0.0,
                    "expected_profit_change": 0.12,
                    "expected_cash_change": 0.05,
                    "explanation": "Reducing refunds preserves revenue and improves profit.",
                },
                confidence=DecisionConfidence.MEDIUM.value,
                evidence=[
                    {
                        "source_type": EvidenceSource.KPI.value,
                        "source_id": "refund_rate",
                        "description": f"Refund rate = {refund_rate * 100:.1f}%",
                    }
                ],
            )
        )
        return recommendations

    def _revenue_falling(
        self,
        insights: List[Dict[str, Any]],
        kpis: Dict[str, Any],
        state: Optional[Dict[str, Any]] = None,
    ) -> List[Recommendation]:
        recommendations = []
        revenue = kpis.get("gross_sales")
        revenue_baseline = kpis.get("gross_sales_baseline")
        if revenue is None or revenue_baseline is None or revenue_baseline == 0:
            return recommendations
        if (revenue_baseline - revenue) / revenue_baseline < self.REVENUE_DROP_THRESHOLD:
            return recommendations

        recommendations.append(
            Recommendation(
                category=DecisionCategory.OPERATIONS.value,
                severity=DecisionSeverity.HIGH.value,
                title=f"Investigate revenue drop ({((revenue_baseline - revenue) / revenue_baseline) * 100:.0f}%)",
                description=f"Revenue fell from {revenue_baseline:,.0f} to {revenue:,.0f}.",
                rationale="A sharp revenue drop requires root cause analysis across traffic, conversion, and pricing.",
                recommended_action="Check traffic sources, conversion rate, and top SKU performance; review recent pricing or listing changes.",
                expected_impact={
                    "expected_revenue_change": 0.10,
                    "expected_profit_change": 0.05,
                    "expected_cash_change": 0.0,
                    "explanation": "Identifying and fixing the cause can recover revenue with minimal upfront cost.",
                },
                confidence=DecisionConfidence.LOW.value,
                evidence=[
                    {
                        "source_type": EvidenceSource.KPI.value,
                        "source_id": "gross_sales",
                        "description": f"Revenue {revenue:,.0f} vs baseline {revenue_baseline:,.0f}",
                    }
                ],
            )
        )
        return recommendations
