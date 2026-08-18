"""Advertising explanation engine."""

from typing import Any, Dict, Optional

from commerceos.intelligence.analyzers.comparisons import compare_metrics, describe_change, format_currency, format_pct
from commerceos.intelligence.constants import InsightCategory, InsightSeverity


ROAS_THRESHOLD = 2.0  # placeholder break-even target


def explain_advertising(
    current: Dict[str, Any],
    previous: Dict[str, Any],
    currency: str = "IDR",
) -> Optional[Dict[str, Any]]:
    """Generate a human-readable explanation of advertising changes."""
    comparison = compare_metrics(current, previous)
    spend = comparison.get("ad_spend")
    roas = comparison.get("roas")
    if spend is None or spend["current"] is None or spend["previous"] is None:
        return None

    spend_delta_pct = spend["delta_pct"] or 0
    change_word = describe_change(spend_delta_pct)
    explanation = (
        f"Ad spend {change_word} {format_pct(spend_delta_pct)} from "
        f"{format_currency(spend['previous'], currency)} to {format_currency(spend['current'], currency)}."
    )

    severity = InsightSeverity.INFO
    if roas and roas["current"] is not None and roas["previous"] is not None:
        roas_change = roas["delta_pct"] or 0
        explanation += f" ROAS {describe_change(roas_change)} from {roas['previous']:.2f} to {roas['current']:.2f}."
        if roas["current"] < ROAS_THRESHOLD:
            severity = InsightSeverity.HIGH

    if spend_delta_pct >= 50:
        severity = InsightSeverity.WARNING if severity.value < InsightSeverity.WARNING.value else severity

    return {
        "category": InsightCategory.ADVERTISING.value,
        "severity": severity.value,
        "title": f"Ad spend {change_word} {format_pct(spend_delta_pct)}",
        "explanation": explanation,
        "evidence": comparison,
    }
