"""Deterministic decision rules: advertising.

Rules consume insights, KPIs, and commerce state and produce Recommendations.
No execution. No LLM.
"""

from typing import Any, Dict, List, Optional

from commerceos.decision.constants import DecisionCategory, DecisionConfidence, DecisionSeverity, EvidenceSource
from commerceos.decision.recommendation import Recommendation


class AdvertisingRules:
    """Rules for advertising decisions."""

    ROAS_LOW_THRESHOLD = 2.0
    ROAS_CRITICAL_THRESHOLD = 1.0
    SPEND_SURGE_THRESHOLD = 0.50
    CTR_ROAS_GAP_THRESHOLD = 0.05

    def evaluate(
        self,
        insights: List[Dict[str, Any]],
        kpis: Dict[str, Any],
        state: Optional[Dict[str, Any]] = None,
    ) -> List[Recommendation]:
        recommendations = []
        recommendations.extend(self._roas_low(insights, kpis))
        recommendations.extend(self._spend_surge(insights, kpis))
        recommendations.extend(self._high_ctr_low_roas(insights, kpis))
        return recommendations

    def _roas_low(self, insights: List[Dict[str, Any]], kpis: Dict[str, Any]) -> List[Recommendation]:
        recommendations = []
        for insight in insights:
            if insight.get("category") != "advertising":
                continue
            if "ROAS" not in insight.get("title", "") and "roas" not in insight.get("explanation", "").lower():
                continue
            roas = kpis.get("roas")
            if roas is None:
                continue
            if roas < self.ROAS_CRITICAL_THRESHOLD:
                severity = DecisionSeverity.CRITICAL
                action = "Pause the underperforming campaign and review targeting before resuming."
                confidence = DecisionConfidence.HIGH
            elif roas < self.ROAS_LOW_THRESHOLD:
                severity = DecisionSeverity.HIGH
                action = "Reduce campaign budget by 20% and review keyword / audience targeting."
                confidence = DecisionConfidence.MEDIUM
            else:
                continue
            recommendations.append(
                Recommendation(
                    category=DecisionCategory.ADVERTISING.value,
                    severity=severity.value,
                    title=f"Reduce advertising spend (ROAS {roas:.2f})",
                    description=f"ROAS is {roas:.2f}, below the {self.ROAS_LOW_THRESHOLD:.2f} break-even target.",
                    rationale="Low ROAS means each ad dollar returns less than target revenue. Reducing spend limits losses while targeting is reviewed.",
                    recommended_action=action,
                    expected_impact={
                        "expected_revenue_change": -0.10,
                        "expected_profit_change": 0.15,
                        "expected_cash_change": 0.05,
                        "explanation": "Lower spend reduces revenue slightly but improves profit and cash preservation.",
                    },
                    confidence=confidence.value,
                    evidence=[
                        {
                            "source_type": EvidenceSource.INSIGHT.value,
                            "source_id": insight.get("id"),
                            "description": insight.get("title", "ROAS insight"),
                        },
                        {
                            "source_type": EvidenceSource.KPI.value,
                            "source_id": "roas",
                            "description": f"Current ROAS = {roas:.2f}",
                        },
                    ],
                )
            )
        return recommendations

    def _spend_surge(self, insights: List[Dict[str, Any]], kpis: Dict[str, Any]) -> List[Recommendation]:
        recommendations = []
        ad_spend = kpis.get("ad_spend")
        ad_spend_baseline = kpis.get("ad_spend_baseline")
        if ad_spend is None or ad_spend_baseline is None or ad_spend_baseline == 0:
            return recommendations
        if (ad_spend - ad_spend_baseline) / ad_spend_baseline < self.SPEND_SURGE_THRESHOLD:
            return recommendations

        recommendations.append(
            Recommendation(
                category=DecisionCategory.ADVERTISING.value,
                severity=DecisionSeverity.WARNING.value,
                title=f"Review ad spend surge (+{((ad_spend - ad_spend_baseline) / ad_spend_baseline) * 100:.0f}%)",
                description=f"Ad spend increased from {ad_spend_baseline:,.0f} to {ad_spend:,.0f}.",
                rationale="A rapid spend increase without a proportional revenue increase can burn cash. Audit campaign budgets and bids.",
                recommended_action="Review campaign budgets and bidding rules; cap daily spend until ROAS recovers.",
                expected_impact={
                    "expected_revenue_change": -0.05,
                    "expected_profit_change": 0.10,
                    "expected_cash_change": 0.08,
                    "explanation": "Capping spend protects cash with limited revenue impact.",
                },
                confidence=DecisionConfidence.MEDIUM.value,
                evidence=[
                    {
                        "source_type": EvidenceSource.KPI.value,
                        "source_id": "ad_spend",
                        "description": f"Ad spend {ad_spend:,.0f} vs baseline {ad_spend_baseline:,.0f}",
                    }
                ],
            )
        )
        return recommendations

    def _high_ctr_low_roas(self, insights: List[Dict[str, Any]], kpis: Dict[str, Any]) -> List[Recommendation]:
        recommendations = []
        ctr = kpis.get("ctr")
        roas = kpis.get("roas")
        if ctr is None or roas is None:
            return recommendations
        if ctr < self.CTR_ROAS_GAP_THRESHOLD or roas >= self.ROAS_LOW_THRESHOLD:
            return recommendations

        recommendations.append(
            Recommendation(
                category=DecisionCategory.ADVERTISING.value,
                severity=DecisionSeverity.WARNING.value,
                title="Review keywords: high CTR but low ROAS",
                description=f"CTR is {ctr:.2%} but ROAS is only {roas:.2f}.",
                rationale="High click-through with poor return suggests clicks are not converting or targeting is too broad.",
                recommended_action="Review search keywords and product detail pages; add negative keywords and pause broad match terms.",
                expected_impact={
                    "expected_revenue_change": 0.0,
                    "expected_profit_change": 0.10,
                    "expected_cash_change": 0.05,
                    "explanation": "Better targeting reduces wasted clicks and improves profit without major revenue loss.",
                },
                confidence=DecisionConfidence.MEDIUM.value,
                evidence=[
                    {
                        "source_type": EvidenceSource.KPI.value,
                        "source_id": "ctr",
                        "description": f"CTR = {ctr:.2%}",
                    },
                    {
                        "source_type": EvidenceSource.KPI.value,
                        "source_id": "roas",
                        "description": f"ROAS = {roas:.2f}",
                    },
                ],
            )
        )
        return recommendations
