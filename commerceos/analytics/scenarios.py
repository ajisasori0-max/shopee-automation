"""WP5.5 — Scenario Engine.

What-if analysis isolated from production state. Examples:
- Advertising +20% ad spend → expected revenue, gross profit, contribution profit, cash impact.
- Sales decline -20% → gross profit impact, cash impact, inventory implications.
- Supplier delay lead time 7 → 14 days → safety stock, reorder point, stockout risk, cash requirement.

Scenarios are reproducible, parameterized, auditable, and clearly labeled as scenarios, not actuals.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from commerceos.analytics.engine import AdvancedAnalyticsEngine
from commerceos.analytics.finance import FinancialForecastingEngine
from commerceos.analytics.forecasting import DemandForecastingEngine
from commerceos.analytics.inventory import InventoryIntelligenceEngine


STORE_ID = "store-ppm-001"


@dataclass
class ScenarioResult:
    scenario_id: str
    scenario_type: str
    parameters: Dict[str, Any]
    baseline: Dict[str, Any]
    scenario: Dict[str, Any]
    delta: Dict[str, Any]
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "scenario_type": self.scenario_type,
            "parameters": self.parameters,
            "baseline": self.baseline,
            "scenario": self.scenario,
            "delta": self.delta,
            "notes": self.notes,
        }


class ScenarioEngine:
    """Run isolated, reproducible what-if scenarios."""

    def __init__(self, session: Session, store_id: str = STORE_ID):
        self.session = session
        self.store_id = store_id
        self.analytics = AdvancedAnalyticsEngine(session, store_id)
        self.finance = FinancialForecastingEngine(session, store_id)
        self.forecaster = DemandForecastingEngine(session, store_id)
        self.inventory = InventoryIntelligenceEngine(session, store_id)

    def ad_spend_increase(self, increase_pct: float = 20.0, horizon_days: int = 30) -> Dict[str, Any]:
        """Scenario: increase ad spend by X% and estimate revenue/impact."""
        baseline_pnl = self.finance.forecast_pnl(horizon_days=horizon_days)
        baseline_ad = self.forecaster.ad_spend_forecast(horizon_days=horizon_days)
        baseline_ad_spend = sum(p.value for p in baseline_ad.points) if baseline_ad.points else 0.0

        scenario_ad_spend = baseline_ad_spend * (1 + increase_pct / 100)
        additional_spend = scenario_ad_spend - baseline_ad_spend

        # Assume revenue elasticity to ad spend: 1% ad spend → 0.5% revenue.
        elasticity = 0.5
        scenario_revenue = baseline_pnl["forecast_revenue"] * (1 + (increase_pct / 100 * elasticity))

        fee_ratio = baseline_pnl["marketplace_fees"] / baseline_pnl["forecast_revenue"] if baseline_pnl["forecast_revenue"] else 0.0
        scenario_fees = scenario_revenue * fee_ratio
        scenario_contribution = scenario_revenue - scenario_fees - scenario_ad_spend

        baseline_contribution = baseline_pnl["contribution_profit"]
        delta_contribution = scenario_contribution - baseline_contribution

        return ScenarioResult(
            scenario_id=f"ad-spend-+{increase_pct:.0f}pct",
            scenario_type="ad_spend_increase",
            parameters={"increase_pct": increase_pct, "horizon_days": horizon_days, "elasticity": elasticity},
            baseline={
                "forecast_revenue": baseline_pnl["forecast_revenue"],
                "advertising": baseline_ad_spend,
                "contribution_profit": baseline_contribution,
            },
            scenario={
                "forecast_revenue": round(scenario_revenue, 2),
                "advertising": round(scenario_ad_spend, 2),
                "contribution_profit": round(scenario_contribution, 2),
            },
            delta={
                "forecast_revenue": round(scenario_revenue - baseline_pnl["forecast_revenue"], 2),
                "advertising": round(additional_spend, 2),
                "contribution_profit": round(delta_contribution, 2),
            },
            notes=[
                "Scenario uses assumed ad-to-revenue elasticity of 0.5.",
                "COGS unavailable; profit is contribution profit before COGS.",
            ],
        ).to_dict()

    def sales_decline(self, decline_pct: float = 20.0, horizon_days: int = 30) -> Dict[str, Any]:
        """Scenario: revenue declines by X% and estimate impact."""
        baseline_pnl = self.finance.forecast_pnl(horizon_days=horizon_days)
        baseline_revenue = baseline_pnl["forecast_revenue"]
        scenario_revenue = baseline_revenue * (1 - decline_pct / 100)

        fee_ratio = baseline_pnl["marketplace_fees"] / baseline_revenue if baseline_revenue else 0.0
        ad_ratio = baseline_pnl["advertising"] / baseline_revenue if baseline_revenue else 0.0
        scenario_fees = scenario_revenue * fee_ratio
        scenario_ad = scenario_revenue * ad_ratio
        scenario_contribution = scenario_revenue - scenario_fees - scenario_ad

        baseline_contribution = baseline_pnl["contribution_profit"]
        delta_contribution = scenario_contribution - baseline_contribution

        # Inventory implication: slower velocity means more days of cover.
        inventory = self.inventory.recommend()
        slower_skus = []
        for rec in inventory["recommendations"]:
            if rec["daily_velocity"] > 0:
                slower_velocity = rec["daily_velocity"] * (1 - decline_pct / 100)
                slower_coverage = rec["available_stock"] / slower_velocity
                slower_skus.append({
                    "sku": rec["sku"],
                    "baseline_coverage_days": rec["coverage_days"],
                    "scenario_coverage_days": round(slower_coverage, 1),
                })

        return ScenarioResult(
            scenario_id=f"sales-decline-{decline_pct:.0f}pct",
            scenario_type="sales_decline",
            parameters={"decline_pct": decline_pct, "horizon_days": horizon_days},
            baseline={
                "forecast_revenue": baseline_revenue,
                "contribution_profit": baseline_contribution,
            },
            scenario={
                "forecast_revenue": round(scenario_revenue, 2),
                "contribution_profit": round(scenario_contribution, 2),
            },
            delta={
                "forecast_revenue": round(scenario_revenue - baseline_revenue, 2),
                "contribution_profit": round(delta_contribution, 2),
            },
            notes=[
                "Assumes fees and ad spend scale proportionally with revenue.",
                "Inventory coverage increases as velocity declines.",
                f"{len(slower_skus)} SKU(s) analyzed for inventory impact.",
            ],
        ).to_dict()

    def supplier_delay(
        self,
        sku: str,
        baseline_lead_time: int = 7,
        scenario_lead_time: int = 14,
    ) -> Dict[str, Any]:
        """Scenario: supplier lead time increases and estimate stockout risk/cash requirement."""
        inventory = self.inventory.recommend(sku=sku)
        if not inventory["recommendations"]:
            return {
                "scenario_id": f"supplier-delay-{sku}",
                "scenario_type": "supplier_delay",
                "parameters": {"sku": sku, "baseline_lead_time": baseline_lead_time, "scenario_lead_time": scenario_lead_time},
                "error": f"SKU {sku} not found or has no inventory data.",
            }

        rec = inventory["recommendations"][0]
        velocity = rec["daily_velocity"]
        available = rec["available_stock"]

        baseline_safety = 7
        baseline_reorder_point = int(velocity * (baseline_lead_time + baseline_safety))
        scenario_reorder_point = int(velocity * (scenario_lead_time + baseline_safety))

        baseline_coverage = available / velocity if velocity > 0 else 999.0
        scenario_stockout_risk = baseline_coverage < scenario_lead_time

        additional_stock_needed = max(0, scenario_reorder_point - baseline_reorder_point)
        cash_required = additional_stock_needed * (rec["selling_price"] or 0)

        return ScenarioResult(
            scenario_id=f"supplier-delay-{sku}",
            scenario_type="supplier_delay",
            parameters={"sku": sku, "baseline_lead_time": baseline_lead_time, "scenario_lead_time": scenario_lead_time},
            baseline={
                "lead_time_days": baseline_lead_time,
                "reorder_point": baseline_reorder_point,
                "coverage_days": rec["coverage_days"],
            },
            scenario={
                "lead_time_days": scenario_lead_time,
                "reorder_point": scenario_reorder_point,
                "stockout_risk": scenario_stockout_risk,
                "additional_stock_needed": additional_stock_needed,
                "cash_required": round(cash_required, 2) if cash_required else 0.0,
            },
            delta={
                "lead_time_days": scenario_lead_time - baseline_lead_time,
                "reorder_point": scenario_reorder_point - baseline_reorder_point,
            },
            notes=[
                "Safety stock days assumed constant at 7.",
                "Cash required is an estimate based on selling price and additional stock.",
            ],
        ).to_dict()

    def run(
        self,
        scenario_type: str,
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Dispatch a scenario by type."""
        if scenario_type == "ad_spend_increase":
            return self.ad_spend_increase(**parameters)
        if scenario_type == "sales_decline":
            return self.sales_decline(**parameters)
        if scenario_type == "supplier_delay":
            return self.supplier_delay(**parameters)
        return {
            "scenario_id": "unknown",
            "scenario_type": scenario_type,
            "parameters": parameters,
            "error": f"Unknown scenario type: {scenario_type}",
        }
