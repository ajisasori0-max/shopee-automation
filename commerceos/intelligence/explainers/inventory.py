"""Inventory explanation engine."""

from typing import Any, Dict, List, Optional

from commerceos.intelligence.analyzers.comparisons import format_currency
from commerceos.intelligence.constants import InsightCategory, InsightSeverity


# Placeholder threshold: flag SKUs with coverage < 7 days if available.
LOW_COVERAGE_DAYS = 7


def explain_inventory(
    inventory_items: List[Dict[str, Any]],
    currency: str = "IDR",
) -> List[Dict[str, Any]]:
    """Generate inventory insights from product/inventory data."""
    insights = []
    low_coverage = [
        item for item in inventory_items
        if item.get("coverage_days") is not None and item["coverage_days"] < LOW_COVERAGE_DAYS
    ]
    if low_coverage:
        low_coverage.sort(key=lambda x: x.get("coverage_days", 0))
        skus = [item.get("sku", "unknown") for item in low_coverage[:5]]
        insights.append({
            "category": InsightCategory.INVENTORY.value,
            "severity": InsightSeverity.WARNING.value,
            "title": f"{len(low_coverage)} SKUs below {LOW_COVERAGE_DAYS}-day coverage",
            "explanation": (
                f"The following SKUs have coverage below {LOW_COVERAGE_DAYS} days: "
                f"{', '.join(skus)}. Review stock or reorder soon."
            ),
            "evidence": {
                "count": len(low_coverage),
                "skus": skus,
                "threshold_days": LOW_COVERAGE_DAYS,
            },
        })
    return insights


def explain_inventory_summary(
    total_skus: int,
    low_coverage_count: int,
    total_stock_value: Optional[float],
    currency: str = "IDR",
) -> Dict[str, Any]:
    return {
        "category": InsightCategory.INVENTORY.value,
        "severity": InsightSeverity.INFO.value,
        "title": "Inventory summary",
        "explanation": (
            f"{total_skus} SKUs tracked, {low_coverage_count} below {LOW_COVERAGE_DAYS} days coverage. "
            f"Total stock value: {format_currency(total_stock_value, currency)}."
        ),
        "evidence": {
            "total_skus": total_skus,
            "low_coverage_count": low_coverage_count,
            "total_stock_value": total_stock_value,
            "currency": currency,
        },
    }
