"""Revenue explanation engine."""

from typing import Any, Dict, Optional

from commerceos.intelligence.analyzers.comparisons import compare_metrics, describe_change, format_currency, format_pct
from commerceos.intelligence.constants import InsightCategory, InsightSeverity


def explain_revenue_change(
    current: Dict[str, Any],
    previous: Dict[str, Any],
    currency: str = "IDR",
) -> Optional[Dict[str, Any]]:
    """Generate a human-readable explanation of revenue change."""
    comparison = compare_metrics(current, previous)
    rev = comparison.get("gross_sales")
    orders = comparison.get("order_count")
    aov = comparison.get("aov")
    if rev is None or rev["current"] is None or rev["previous"] is None:
        return None

    delta_pct = rev["delta_pct"] or 0
    change_word = describe_change(delta_pct)
    explanation = (
        f"Revenue {change_word} {format_pct(delta_pct)} from {format_currency(rev['previous'], currency)} "
        f"to {format_currency(rev['current'], currency)}."
    )
    if orders and orders["current"] is not None and orders["previous"] is not None:
        order_change = orders["delta_pct"] or 0
        explanation += f" Order count {describe_change(order_change)}."
    if aov and aov["current"] is not None and aov["previous"] is not None:
        aov_change = aov["delta_pct"] or 0
        explanation += f" Average order value {describe_change(aov_change)}."

    severity = InsightSeverity.INFO
    if abs(delta_pct) >= 30:
        severity = InsightSeverity.HIGH
    elif abs(delta_pct) >= 10:
        severity = InsightSeverity.WARNING
    elif abs(delta_pct) >= 5:
        severity = InsightSeverity.NOTICE

    return {
        "category": InsightCategory.REVENUE.value,
        "severity": severity.value,
        "title": f"Revenue {change_word} {format_pct(delta_pct)}",
        "explanation": explanation,
        "evidence": comparison,
    }
