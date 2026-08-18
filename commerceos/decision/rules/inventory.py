"""Deterministic decision rules: inventory."""

from typing import Any, Dict, List, Optional

from commerceos.decision.constants import DecisionCategory, DecisionConfidence, DecisionSeverity, EvidenceSource
from commerceos.decision.recommendation import Recommendation


class InventoryRules:
    """Rules for inventory decisions."""

    COVERAGE_LOW_THRESHOLD = 7  # days
    ZERO_STOCK_SKU_THRESHOLD = 1

    def evaluate(
        self,
        insights: List[Dict[str, Any]],
        kpis: Dict[str, Any],
        state: Optional[Dict[str, Any]] = None,
    ) -> List[Recommendation]:
        recommendations = []
        recommendations.extend(self._low_coverage(insights, kpis, state))
        recommendations.extend(self._zero_stock(insights, kpis, state))
        return recommendations

    def _low_coverage(
        self,
        insights: List[Dict[str, Any]],
        kpis: Dict[str, Any],
        state: Optional[Dict[str, Any]] = None,
    ) -> List[Recommendation]:
        recommendations = []
        coverage = kpis.get("inventory_coverage_days")
        if coverage is None or coverage >= self.COVERAGE_LOW_THRESHOLD:
            return recommendations

        recommendations.append(
            Recommendation(
                category=DecisionCategory.INVENTORY.value,
                severity=DecisionSeverity.WARNING.value,
                title=f"Reorder inventory ({coverage:.0f} days coverage)",
                description=f"Inventory coverage is {coverage:.0f} days, below the {self.COVERAGE_LOW_THRESHOLD}-day safety threshold.",
                rationale="Low coverage increases the risk of stockouts and lost sales during demand spikes.",
                recommended_action="Calculate reorder quantity based on recent velocity and place purchase orders for at-risk SKUs.",
                expected_impact={
                    "expected_revenue_change": 0.05,
                    "expected_profit_change": 0.03,
                    "expected_cash_change": -0.10,
                    "explanation": "Restocking prevents lost sales but ties up cash in inventory.",
                },
                confidence=DecisionConfidence.MEDIUM.value,
                evidence=[
                    {
                        "source_type": EvidenceSource.KPI.value,
                        "source_id": "inventory_coverage_days",
                        "description": f"Coverage = {coverage:.0f} days",
                    }
                ],
            )
        )
        return recommendations

    def _zero_stock(
        self,
        insights: List[Dict[str, Any]],
        kpis: Dict[str, Any],
        state: Optional[Dict[str, Any]] = None,
    ) -> List[Recommendation]:
        recommendations = []
        zero_stock_skus = kpis.get("zero_stock_skus", 0)
        if zero_stock_skus < self.ZERO_STOCK_SKU_THRESHOLD:
            return recommendations

        recommendations.append(
            Recommendation(
                category=DecisionCategory.INVENTORY.value,
                severity=DecisionSeverity.HIGH.value,
                title=f"Restock {zero_stock_skus} out-of-stock SKUs",
                description=f"{zero_stock_skus} SKUs currently have zero available stock.",
                rationale="Out-of-stock SKUs directly lose revenue. Restocking high-velocity items is the highest priority.",
                recommended_action="Identify top-selling out-of-stock SKUs and expedite replenishment.",
                expected_impact={
                    "expected_revenue_change": 0.15,
                    "expected_profit_change": 0.05,
                    "expected_cash_change": -0.15,
                    "explanation": "Restocking high-velocity SKUs restores revenue but requires cash outlay.",
                },
                confidence=DecisionConfidence.HIGH.value,
                evidence=[
                    {
                        "source_type": EvidenceSource.KPI.value,
                        "source_id": "zero_stock_skus",
                        "description": f"{zero_stock_skus} SKUs out of stock",
                    }
                ],
            )
        )
        return recommendations
