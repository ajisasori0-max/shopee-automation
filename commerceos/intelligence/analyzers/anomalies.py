"""Deterministic anomaly detection.

Threshold-based rules only. No ML, no LLM.
"""

from typing import Any, Dict, List, Optional

from commerceos.intelligence.analyzers.trends import TrendPoint, detect_anomaly
from commerceos.intelligence.constants import InsightCategory, InsightSeverity, TrendPeriod


AnomalyRule = Dict[str, Any]


DEFAULT_ANOMALY_RULES: List[AnomalyRule] = [
    {
        "metric": "gross_sales",
        "threshold": 0.30,
        "direction": "both",
        "category": InsightCategory.REVENUE,
        "title_template": "Revenue deviated {delta_pct:.0f}% {direction} from baseline",
        "explanation_template": "Revenue changed from {baseline:,.0f} to {value:,.0f} ({delta_pct:.1f}% {direction}).",
        "severity": InsightSeverity.WARNING,
    },
    {
        "metric": "order_count",
        "threshold": 0.40,
        "direction": "down",
        "category": InsightCategory.REVENUE,
        "title_template": "Order count dropped {delta_pct:.0f}%",
        "explanation_template": "Orders fell from {baseline:.0f} to {value:.0f} ({delta_pct:.1f}% drop).",
        "severity": InsightSeverity.HIGH,
    },
    {
        "metric": "roas",
        "threshold": 0.30,
        "direction": "down",
        "category": InsightCategory.ADVERTISING,
        "title_template": "ROAS fell {delta_pct:.0f}% below baseline",
        "explanation_template": "ROAS declined from {baseline:.2f} to {value:.2f} ({delta_pct:.1f}% drop).",
        "severity": InsightSeverity.WARNING,
    },
    {
        "metric": "ad_spend",
        "threshold": 0.50,
        "direction": "up",
        "category": InsightCategory.ADVERTISING,
        "title_template": "Ad spend increased {delta_pct:.0f}%",
        "explanation_template": "Ad spend rose from {baseline:,.0f} to {value:,.0f} ({delta_pct:.1f}% increase).",
        "severity": InsightSeverity.WARNING,
    },
]


def evaluate_anomalies(trends: List[TrendPoint], rules: Optional[List[AnomalyRule]] = None) -> List[Dict[str, Any]]:
    """Return anomaly candidates for trend points that breach thresholds."""
    rules = rules or DEFAULT_ANOMALY_RULES
    results: List[Dict[str, Any]] = []
    for rule in rules:
        for point in trends:
            if point.metric != rule["metric"] or point.period != TrendPeriod.DAY_OVER_DAY:
                continue
            if point.value is None or point.baseline is None:
                continue
            if detect_anomaly(point.value, point.baseline, rule["threshold"], rule.get("direction", "both")):
                direction = _direction_word(point.delta)
                context = {
                    "metric": point.metric,
                    "value": point.value,
                    "baseline": point.baseline,
                    "delta": point.delta,
                    "delta_pct": point.delta_pct or 0,
                    "direction": direction,
                    "period": point.period.value,
                    "category": rule["category"].value,
                }
                results.append({
                    "category": rule["category"].value,
                    "severity": rule["severity"].value,
                    "title": rule["title_template"].format(**context),
                    "explanation": rule["explanation_template"].format(**context),
                    "evidence": context,
                })
    return results


def _direction_word(delta: Optional[float]) -> str:
    if delta is None:
        return "changed"
    return "increased" if delta >= 0 else "decreased"
