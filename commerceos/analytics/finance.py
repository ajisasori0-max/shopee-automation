"""WP5.4 — Financial Forecasting.

Actual P&L: Revenue − COGS − Marketplace fees − Advertising − Other known costs.
Forecast P&L: Historical actuals + forecast revenue + forecast costs.
Cash forecast: Opening cash + expected inflows − expected outflows.

Explicitly reports missing inputs rather than fabricating them.
"""

from commerceos.shared.value_objects.primitives import utc_now

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from commerceos.analytics.forecasting import DemandForecastingEngine
from commerceos.commerce.models import AdPerformance, Expense, Order, Payment


STORE_ID = "store-ppm-001"


@dataclass
class PnLStatement:
    period: Dict[str, str]
    revenue: float
    cogs: Optional[float]
    marketplace_fees: float
    advertising: float
    other_costs: Optional[float]
    gross_profit: Optional[float]
    contribution_profit: float
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "period": self.period,
            "revenue": self.revenue,
            "cogs": self.cogs,
            "marketplace_fees": self.marketplace_fees,
            "advertising": self.advertising,
            "other_costs": self.other_costs,
            "gross_profit": self.gross_profit,
            "contribution_profit": self.contribution_profit,
            "notes": self.notes,
        }


class FinancialForecastingEngine:
    """Compute actual and forecast P&L and cash position."""

    def __init__(self, session: Session, store_id: str = STORE_ID):
        self.session = session
        self.store_id = store_id
        self.forecaster = DemandForecastingEngine(session, store_id)

    def actual_pnl(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Compute actual P&L for a period. COGS is reported as missing if unavailable."""
        end = end or utc_now()
        start = start or (end - timedelta(days=30))

        revenue = (
            self.session.query(func.sum(Order.total_amount))
            .filter(
                Order.store_id == self.store_id,
                Order.ordered_at >= start,
                Order.ordered_at < end,
                Order.status.notin_(["cancelled"]),
            )
            .scalar()
        ) or 0.0

        marketplace_fees = float(
            self.session.query(func.sum(Payment.fee_amount))
            .filter(
                Payment.store_id == self.store_id,
                Payment.paid_at >= start,
                Payment.paid_at < end,
            )
            .scalar()
        ) or 0.0

        advertising = float(
            self.session.query(func.sum(AdPerformance.spend))
            .filter(
                AdPerformance.store_id == self.store_id,
                AdPerformance.date >= start.date(),
                AdPerformance.date < end.date(),
            )
            .scalar() or 0
        )

        other_costs = (
            self.session.query(func.sum(Expense.amount))
            .filter(
                Expense.store_id == self.store_id,
                Expense.incurred_at >= start,
                Expense.incurred_at < end,
            )
            .scalar()
        )
        if other_costs is not None:
            other_costs = float(other_costs)

        cogs = None  # Not available in canonical tables
        revenue = float(revenue)
        contribution_profit = revenue - marketplace_fees - advertising
        gross_profit = (contribution_profit - cogs) if cogs is not None else None

        notes = []
        if cogs is None:
            notes.append("COGS is unavailable; gross profit cannot be computed. Contribution profit is before COGS.")
        if other_costs is None:
            notes.append("Other operating costs are unavailable.")
        else:
            contribution_profit -= other_costs

        return PnLStatement(
            period={"start": start.isoformat(), "end": end.isoformat()},
            revenue=revenue,
            cogs=cogs,
            marketplace_fees=marketplace_fees,
            advertising=advertising,
            other_costs=other_costs,
            gross_profit=gross_profit,
            contribution_profit=contribution_profit,
            notes=notes,
        ).to_dict()

    def forecast_pnl(
        self,
        horizon_days: int = 30,
    ) -> Dict[str, Any]:
        """Forecast P&L from sales forecast and recent cost ratios."""
        sales = self.forecaster.sales_forecast(horizon_days=horizon_days)
        if not sales.points:
            return {
                "horizon_days": horizon_days,
                "forecast_revenue": 0.0,
                "marketplace_fees": 0.0,
                "advertising": 0.0,
                "cogs": None,
                "contribution_profit": 0.0,
                "notes": ["No sales forecast available; P&L forecast cannot be computed."],
            }

        forecast_revenue = sum(p.value for p in sales.points)

        # Use recent actual cost ratios.
        end = utc_now()
        start = end - timedelta(days=30)
        actual = self.actual_pnl(start, end)
        revenue_actual = actual["revenue"]
        fee_ratio = (actual["marketplace_fees"] / revenue_actual) if revenue_actual else 0.0
        ad_ratio = (actual["advertising"] / revenue_actual) if revenue_actual else 0.0

        forecast_fees = forecast_revenue * fee_ratio
        forecast_advertising = forecast_revenue * ad_ratio
        contribution_profit = forecast_revenue - forecast_fees - forecast_advertising

        return {
            "horizon_days": horizon_days,
            "forecast_revenue": round(forecast_revenue, 2),
            "marketplace_fees": round(forecast_fees, 2),
            "advertising": round(forecast_advertising, 2),
            "cogs": None,
            "contribution_profit": round(contribution_profit, 2),
            "notes": ["P&L forecast based on sales forecast and recent cost ratios. COGS unavailable."],
        }

    def cash_forecast(
        self,
        horizon_days: int = 30,
    ) -> Dict[str, Any]:
        """Forecast cash position. Requires opening cash balance; reports missing if unavailable."""
        opening_cash = None  # No cash balance table exists yet.

        sales = self.forecaster.sales_forecast(horizon_days=horizon_days)
        expected_inflows = sum(p.value for p in sales.points) if sales.points else None

        # Expected outflows: recent fee ratio, ad spend, other costs.
        end = utc_now()
        start = end - timedelta(days=30)
        actual = self.actual_pnl(start, end)
        revenue_actual = actual["revenue"]
        expected_outflows = None
        if expected_inflows is not None:
            fee_ratio = (actual["marketplace_fees"] / revenue_actual) if revenue_actual else 0.0
            ad_ratio = (actual["advertising"] / revenue_actual) if revenue_actual else 0.0
            expected_outflows = expected_inflows * (fee_ratio + ad_ratio)
            if actual.get("other_costs") is not None:
                expected_outflows += actual["other_costs"] / 30 * horizon_days

        notes = []
        if opening_cash is None:
            notes.append("Opening cash balance unavailable; forecast is incomplete.")
        if expected_inflows is None:
            notes.append("Expected inflows unavailable; forecast is incomplete.")

        projected_cash = None
        if opening_cash is not None and expected_inflows is not None and expected_outflows is not None:
            projected_cash = opening_cash + expected_inflows - expected_outflows

        return {
            "horizon_days": horizon_days,
            "opening_cash": opening_cash,
            "expected_inflows": round(expected_inflows, 2) if expected_inflows is not None else None,
            "expected_outflows": round(expected_outflows, 2) if expected_outflows is not None else None,
            "projected_cash": round(projected_cash, 2) if projected_cash is not None else None,
            "notes": notes,
        }

    def summary(self, days: int = 30, forecast_days: int = 30) -> Dict[str, Any]:
        end = utc_now()
        start = end - timedelta(days=days)
        return {
            "generated_at": utc_now().isoformat(),
            "actual_pnl": self.actual_pnl(start, end),
            "forecast_pnl": self.forecast_pnl(forecast_days),
            "cash_forecast": self.cash_forecast(forecast_days),
        }
