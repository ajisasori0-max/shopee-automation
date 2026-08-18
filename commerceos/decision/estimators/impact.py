"""Impact estimation helpers for proposed decisions.

Estimators are deterministic, rule-based, and produce conservative ranges.
No ML, no LLM, no execution.
"""

from typing import Any, Dict, Optional

from commerceos.decision.constants import DecisionCategory, DecisionConfidence


def _clamp(value: Optional[float], lower: float, upper: float) -> float:
    if value is None:
        return 0.0
    return max(lower, min(upper, value))


def estimate_advertising_impact(
    current_spend: Optional[float],
    current_roas: Optional[float],
    recommended_spend_change: Optional[float] = None,
) -> Dict[str, Any]:
    """Estimate impact of an advertising budget change."""
    if current_spend is None or current_roas is None:
        return {
            "expected_revenue_change": None,
            "expected_profit_change": None,
            "expected_cash_change": None,
            "confidence": DecisionConfidence.LOW.value,
            "explanation": "Insufficient data to estimate advertising impact.",
        }
    change = recommended_spend_change if recommended_spend_change is not None else -0.20
    change = _clamp(change, -0.50, 0.50)
    new_spend = current_spend * (1 + change)
    revenue_change = (new_spend - current_spend) * current_roas
    cash_change = current_spend - new_spend
    profit_change = cash_change * 0.5  # simplified: recovered spend is half profit

    confidence = DecisionConfidence.HIGH if abs(change) <= 0.25 else DecisionConfidence.MEDIUM
    return {
        "expected_revenue_change": round(revenue_change, 2),
        "expected_profit_change": round(profit_change, 2),
        "expected_cash_change": round(cash_change, 2),
        "confidence": confidence.value,
        "explanation": f"Assumes ROAS stays at {current_roas:.2f}. A {change * 100:.0f}% spend change moves revenue by ~{revenue_change:,.0f} and cash by ~{cash_change:,.0f}.",
    }


def estimate_pricing_impact(
    current_revenue: Optional[float],
    current_margin: Optional[float],
    recommended_price_change: Optional[float] = None,
    elasticity: Optional[float] = None,
) -> Dict[str, Any]:
    """Estimate impact of a price change.

    Elasticity defaults to -1.0 (unitary): a 1% price increase reduces volume 1%.
    """
    if current_revenue is None or current_margin is None:
        return {
            "expected_revenue_change": None,
            "expected_profit_change": None,
            "expected_cash_change": None,
            "confidence": DecisionConfidence.LOW.value,
            "explanation": "Insufficient data to estimate pricing impact.",
        }
    price_change = recommended_price_change if recommended_price_change is not None else 0.05
    price_change = _clamp(price_change, -0.20, 0.20)
    elasticity = elasticity if elasticity is not None else -1.0
    volume_change = price_change * elasticity
    revenue_change = current_revenue * ((1 + price_change) * (1 + volume_change) - 1)
    profit_lift = current_revenue * (1 + volume_change) * price_change * current_margin

    confidence = DecisionConfidence.MEDIUM
    return {
        "expected_revenue_change": round(revenue_change, 2),
        "expected_profit_change": round(profit_lift, 2),
        "expected_cash_change": round(profit_lift, 2),
        "confidence": confidence.value,
        "explanation": f"Assumes unit elasticity. A {price_change * 100:.0f}% price change changes volume by {volume_change * 100:.0f}% and profit by ~{profit_lift:,.0f}.",
    }


def estimate_inventory_reorder_impact(
    stockout_skus: Optional[int],
    avg_daily_revenue_per_sku: Optional[float] = None,
    coverage_target: int = 7,
) -> Dict[str, Any]:
    """Estimate impact of restocking out-of-stock or low-coverage SKUs."""
    if stockout_skus is None or stockout_skus <= 0 or avg_daily_revenue_per_sku is None:
        return {
            "expected_revenue_change": None,
            "expected_profit_change": None,
            "expected_cash_change": None,
            "confidence": DecisionConfidence.LOW.value,
            "explanation": "Insufficient data to estimate inventory impact.",
        }
    revenue_recovery = stockout_skus * avg_daily_revenue_per_sku * coverage_target
    cash_required = revenue_recovery * 0.30  # rough COGS estimate
    profit_lift = revenue_recovery * 0.15

    return {
        "expected_revenue_change": round(revenue_recovery, 2),
        "expected_profit_change": round(profit_lift, 2),
        "expected_cash_change": round(-cash_required, 2),
        "confidence": DecisionConfidence.MEDIUM.value,
        "explanation": f"Restocking {stockout_skus} SKUs for {coverage_target} days could recover ~{revenue_recovery:,.0f} revenue.",
    }


def estimate_finance_debt_impact(
    idle_cash: Optional[float],
    interest_rate_annual: Optional[float] = None,
) -> Dict[str, Any]:
    """Estimate impact of using idle cash to pay down debt."""
    if idle_cash is None or idle_cash <= 0:
        return {
            "expected_revenue_change": None,
            "expected_profit_change": None,
            "expected_cash_change": None,
            "confidence": DecisionConfidence.LOW.value,
            "explanation": "Insufficient idle cash data to estimate impact.",
        }
    rate = interest_rate_annual if interest_rate_annual is not None else 0.18
    annual_savings = idle_cash * rate
    return {
        "expected_revenue_change": 0.0,
        "expected_profit_change": round(annual_savings, 2),
        "expected_cash_change": round(-idle_cash, 2),
        "confidence": DecisionConfidence.HIGH.value,
        "explanation": f"Paying down {idle_cash:,.0f} of debt at {rate * 100:.0f}% annual interest saves ~{annual_savings:,.0f}/year.",
    }


def attach_estimates(recommendation) -> Dict[str, Any]:
    """Attach a deterministic impact estimate to a recommendation dict.

    This is a thin dispatcher that can be extended as new categories are added.
    """
    from commerceos.decision.constants import DecisionCategory

    category = recommendation.get("category")
    impact = recommendation.get("expected_impact", {})
    if category == DecisionCategory.ADVERTISING.value and not impact.get("expected_revenue_change"):
        impact = estimate_advertising_impact(
            recommendation.get("current_ad_spend"),
            recommendation.get("current_roas"),
        )
    elif category == DecisionCategory.PRICING.value and not impact.get("expected_revenue_change"):
        impact = estimate_pricing_impact(
            recommendation.get("current_revenue"),
            recommendation.get("current_margin"),
        )
    elif category == DecisionCategory.INVENTORY.value and not impact.get("expected_revenue_change"):
        impact = estimate_inventory_reorder_impact(
            recommendation.get("stockout_skus"),
            recommendation.get("avg_daily_revenue_per_sku"),
        )
    elif category == DecisionCategory.FINANCE.value and not impact.get("expected_revenue_change"):
        impact = estimate_finance_debt_impact(
            recommendation.get("idle_cash"),
        )

    result = dict(recommendation)
    result["expected_impact"] = impact
    return result
