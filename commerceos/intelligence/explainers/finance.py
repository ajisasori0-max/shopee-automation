"""Finance / profit explanation engine."""

from typing import Any, Dict, Optional

from commerceos.intelligence.analyzers.comparisons import compare_metrics, describe_change, format_currency, format_pct
from commerceos.intelligence.constants import InsightCategory, InsightSeverity


PROFIT_MARGIN_THRESHOLD = 0.10  # 10%


def explain_profit(
    current: Dict[str, Any],
    previous: Dict[str, Any],
    currency: str = "IDR",
) -> Optional[Dict[str, Any]]:
    """Generate a human-readable explanation of profit changes."""
    comparison = compare_metrics(current, previous)
    gross_profit = comparison.get("gross_profit")
    margin = comparison.get("gross_margin_pct")
    if gross_profit is None or gross_profit["current"] is None or gross_profit["previous"] is None:
        return None

    delta_pct = gross_profit["delta_pct"] or 0
    change_word = describe_change(delta_pct)
    explanation = (
        f"Gross profit {change_word} {format_pct(delta_pct)} from "
        f"{format_currency(gross_profit['previous'], currency)} to {format_currency(gross_profit['current'], currency)}."
    )

    severity = InsightSeverity.INFO

    if abs(delta_pct) >= 30:
        severity = InsightSeverity.HIGH
    elif margin and margin["current"] is not None:
        margin_pct = margin["current"] / 100 if margin["current"] > 1 else margin["current"]
        if margin_pct < PROFIT_MARGIN_THRESHOLD:
            severity = InsightSeverity.WARNING
        else:
            explanation += f" Gross margin is {margin_pct * 100:.1f}%."
    else:
        explanation += " Gross margin data not available."

    return {
        "category": InsightCategory.PROFIT.value,
        "severity": severity.value,
        "title": f"Gross profit {change_word} {format_pct(delta_pct)}",
        "explanation": explanation,
        "evidence": comparison,
    }
