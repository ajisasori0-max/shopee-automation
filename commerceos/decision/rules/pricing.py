"""Deterministic decision rules: pricing."""

from typing import Any, Dict, List, Optional

from commerceos.decision.constants import DecisionCategory, DecisionConfidence, DecisionSeverity, EvidenceSource
from commerceos.decision.recommendation import Recommendation


class PricingRules:
    """Rules for pricing decisions."""

    MARGIN_LOW_THRESHOLD = 0.10
    AOV_DROP_THRESHOLD = 0.15

    def evaluate(
        self,
        insights: List[Dict[str, Any]],
        kpis: Dict[str, Any],
        state: Optional[Dict[str, Any]] = None,
    ) -> List[Recommendation]:
        recommendations = []
        recommendations.extend(self._margin_pressure(insights, kpis))
        recommendations.extend(self._aov_drop(insights, kpis))
        return recommendations

    def _margin_pressure(self, insights: List[Dict[str, Any]], kpis: Dict[str, Any]) -> List[Recommendation]:
        recommendations = []
        margin = kpis.get("gross_margin_pct")
        if margin is None or margin >= self.MARGIN_LOW_THRESHOLD:
            return recommendations

        recommendations.append(
            Recommendation(
                category=DecisionCategory.PRICING.value,
                severity=DecisionSeverity.HIGH.value,
                title=f"Review pricing: gross margin {margin * 100:.1f}%",
                description=f"Gross margin is {margin * 100:.1f}%, below the {self.MARGIN_LOW_THRESHOLD * 100:.0f}% threshold.",
                rationale="Thin margins leave no room for ads, fees, or refunds. Review costs and pricing before scaling traffic.",
                recommended_action="Audit product costs and fees; consider price increases or bundle offers on low-margin SKUs.",
                expected_impact={
                    "expected_revenue_change": -0.05,
                    "expected_profit_change": 0.20,
                    "expected_cash_change": 0.10,
                    "explanation": "Price increases may reduce volume slightly but significantly improve profitability.",
                },
                confidence=DecisionConfidence.MEDIUM.value,
                evidence=[
                    {
                        "source_type": EvidenceSource.KPI.value,
                        "source_id": "gross_margin_pct",
                        "description": f"Gross margin = {margin * 100:.1f}%",
                    }
                ],
            )
        )
        return recommendations

    def _aov_drop(self, insights: List[Dict[str, Any]], kpis: Dict[str, Any]) -> List[Recommendation]:
        recommendations = []
        aov = kpis.get("aov")
        aov_baseline = kpis.get("aov_baseline")
        if aov is None or aov_baseline is None or aov_baseline == 0:
            return recommendations
        if (aov_baseline - aov) / aov_baseline < self.AOV_DROP_THRESHOLD:
            return recommendations

        recommendations.append(
            Recommendation(
                category=DecisionCategory.PRICING.value,
                severity=DecisionSeverity.WARNING.value,
                title=f"Investigate average order value drop ({((aov_baseline - aov) / aov_baseline) * 100:.0f}%)",
                description=f"AOV fell from {aov_baseline:,.0f} to {aov:,.0f}.",
                rationale="Lower AOV can offset stable order volume and drag down revenue and profit.",
                recommended_action="Introduce bundles, free-shipping thresholds, or upsells to recover AOV.",
                expected_impact={
                    "expected_revenue_change": 0.10,
                    "expected_profit_change": 0.08,
                    "expected_cash_change": 0.05,
                    "explanation": "Recovering AOV lifts revenue and profit without needing new customers.",
                },
                confidence=DecisionConfidence.MEDIUM.value,
                evidence=[
                    {
                        "source_type": EvidenceSource.KPI.value,
                        "source_id": "aov",
                        "description": f"AOV {aov:,.0f} vs baseline {aov_baseline:,.0f}",
                    }
                ],
            )
        )
        return recommendations
