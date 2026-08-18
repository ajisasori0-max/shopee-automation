"""WP5.2 — Demand Forecasting.

Deterministic/statistical baselines for:
- sales
- SKU demand
- inventory depletion
- advertising demand
- cash requirements

Progression:
naive baseline → moving average → weighted moving average → seasonal baseline.

Every forecast includes:
- horizon
- confidence/uncertainty where possible
- source data window
- model/method
- freshness
"""

from commerceos.shared.value_objects.primitives import utc_now

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from commerceos.commerce.models import AdPerformance, Order, OrderItem


STORE_ID = "store-ppm-001"


@dataclass
class ForecastPoint:
    date: str
    value: float
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "value": self.value,
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
        }


@dataclass
class ForecastResult:
    metric: str
    horizon_days: int
    method: str
    source_window_days: int
    generated_at: str
    points: List[ForecastPoint]
    confidence: str
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric": self.metric,
            "horizon_days": self.horizon_days,
            "method": self.method,
            "source_window_days": self.source_window_days,
            "generated_at": self.generated_at,
            "confidence": self.confidence,
            "points": [p.to_dict() for p in self.points],
            "notes": self.notes,
        }


class DemandForecastingEngine:
    """Produce demand forecasts from historical order and ad data."""

    def __init__(self, session: Session, store_id: str = STORE_ID):
        self.session = session
        self.store_id = store_id

    def sales_forecast(
        self,
        horizon_days: int = 7,
        source_window_days: int = 30,
        method: str = "weighted_moving_average",
    ) -> ForecastResult:
        """Forecast daily sales revenue."""
        end = utc_now()
        start = end - timedelta(days=source_window_days)
        daily_sales = self._daily_sales(start, end)

        if not daily_sales:
            return ForecastResult(
                metric="sales_revenue",
                horizon_days=horizon_days,
                method="none",
                source_window_days=source_window_days,
                generated_at=utc_now().isoformat(),
                points=[],
                confidence="none",
                notes=["No historical sales data available for forecasting."],
            )

        values = [v for _, v in daily_sales]
        forecast_value = self._forecast_values(values, method, horizon_days)
        points = []
        for i, val in enumerate(forecast_value):
            day = (end + timedelta(days=i)).date().isoformat()
            points.append(ForecastPoint(date=day, value=round(val, 2)))

        return ForecastResult(
            metric="sales_revenue",
            horizon_days=horizon_days,
            method=method,
            source_window_days=source_window_days,
            generated_at=utc_now().isoformat(),
            points=points,
            confidence="low" if len(values) < 14 else "medium",
            notes=[f"Forecast based on {len(values)} days of historical sales."],
        )

    def sku_demand_forecast(
        self,
        sku: str,
        horizon_days: int = 14,
        source_window_days: int = 30,
        method: str = "moving_average",
    ) -> ForecastResult:
        """Forecast daily unit demand for a single SKU."""
        end = utc_now()
        start = end - timedelta(days=source_window_days)
        daily_units = self._daily_sku_units(sku, start, end)

        if not daily_units:
            return ForecastResult(
                metric=f"sku_units:{sku}",
                horizon_days=horizon_days,
                method="none",
                source_window_days=source_window_days,
                generated_at=utc_now().isoformat(),
                points=[],
                confidence="none",
                notes=[f"No historical demand data for SKU {sku}."],
            )

        values = [v for _, v in daily_units]
        forecast_value = self._forecast_values(values, method, horizon_days)
        points = []
        for i, val in enumerate(forecast_value):
            day = (end + timedelta(days=i)).date().isoformat()
            points.append(ForecastPoint(date=day, value=round(val, 2)))

        return ForecastResult(
            metric=f"sku_units:{sku}",
            horizon_days=horizon_days,
            method=method,
            source_window_days=source_window_days,
            generated_at=utc_now().isoformat(),
            points=points,
            confidence="low" if len(values) < 14 else "medium",
            notes=[f"Forecast based on {len(values)} days of SKU demand."],
        )

    def ad_spend_forecast(
        self,
        horizon_days: int = 7,
        source_window_days: int = 30,
        method: str = "moving_average",
    ) -> ForecastResult:
        """Forecast daily ad spend."""
        end = utc_now()
        start = end - timedelta(days=source_window_days)
        daily_spend = self._daily_ad_spend(start, end)

        if not daily_spend:
            return ForecastResult(
                metric="ad_spend",
                horizon_days=horizon_days,
                method="none",
                source_window_days=source_window_days,
                generated_at=utc_now().isoformat(),
                points=[],
                confidence="none",
                notes=["No historical ad spend data available for forecasting."],
            )

        values = [v for _, v in daily_spend]
        forecast_value = self._forecast_values(values, method, horizon_days)
        points = []
        for i, val in enumerate(forecast_value):
            day = (end + timedelta(days=i)).date().isoformat()
            points.append(ForecastPoint(date=day, value=round(val, 2)))

        return ForecastResult(
            metric="ad_spend",
            horizon_days=horizon_days,
            method=method,
            source_window_days=source_window_days,
            generated_at=utc_now().isoformat(),
            points=points,
            confidence="low" if len(values) < 14 else "medium",
            notes=[f"Forecast based on {len(values)} days of ad spend."],
        )

    def _forecast_values(self, values: List[float], method: str, horizon_days: int) -> List[float]:
        if method == "naive":
            last = values[-1] if values else 0.0
            return [last] * horizon_days
        if method == "moving_average":
            window = min(len(values), 7)
            avg = sum(values[-window:]) / window if window else 0.0
            return [avg] * horizon_days
        if method == "weighted_moving_average":
            return self._weighted_moving_average(values, horizon_days)
        if method == "seasonal_baseline":
            return self._seasonal_baseline(values, horizon_days)
        return [sum(values) / len(values)] * horizon_days if values else [0.0] * horizon_days

    @staticmethod
    def _weighted_moving_average(values: List[float], horizon_days: int) -> List[float]:
        if not values:
            return [0.0] * horizon_days
        weights = list(range(1, len(values) + 1))
        total_weight = sum(weights)
        weighted_avg = sum(v * w for v, w in zip(values, weights)) / total_weight
        return [weighted_avg] * horizon_days

    @staticmethod
    def _seasonal_baseline(values: List[float], horizon_days: int) -> List[float]:
        if len(values) < 14:
            return [sum(values) / len(values)] * horizon_days if values else [0.0] * horizon_days
        # Day-of-week seasonality: average for the same weekday.
        by_weekday: List[List[float]] = [[] for _ in range(7)]
        for i, v in enumerate(values):
            by_weekday[i % 7].append(v)
        weekday_avg = [sum(vals) / len(vals) if vals else 0.0 for vals in by_weekday]
        # Forecast starts at the next index.
        next_idx = len(values)
        return [weekday_avg[(next_idx + i) % 7] for i in range(horizon_days)]

    def _daily_sales(self, start: datetime, end: datetime) -> List[Tuple[str, float]]:
        rows = (
            self.session.query(
                func.date(Order.ordered_at).label("day"),
                func.sum(Order.total_amount).label("revenue"),
            )
            .filter(
                Order.store_id == self.store_id,
                Order.ordered_at >= start,
                Order.ordered_at < end,
                Order.status.notin_(["cancelled"]),
            )
            .group_by(func.date(Order.ordered_at))
            .order_by(func.date(Order.ordered_at))
            .all()
        )
        return [(str(r.day), float(r.revenue or 0)) for r in rows]

    def _daily_sku_units(self, sku: str, start: datetime, end: datetime) -> List[Tuple[str, int]]:
        rows = (
            self.session.query(
                func.date(Order.ordered_at).label("day"),
                func.sum(OrderItem.quantity).label("units"),
            )
            .join(Order, OrderItem.order_id == Order.id)
            .filter(
                Order.store_id == self.store_id,
                OrderItem.sku == sku,
                Order.ordered_at >= start,
                Order.ordered_at < end,
                Order.status.notin_(["cancelled"]),
            )
            .group_by(func.date(Order.ordered_at))
            .order_by(func.date(Order.ordered_at))
            .all()
        )
        return [(str(r.day), int(r.units or 0)) for r in rows]

    def _daily_ad_spend(self, start: datetime, end: datetime) -> List[Tuple[str, float]]:
        rows = (
            self.session.query(
                AdPerformance.date.label("day"),
                func.sum(AdPerformance.spend).label("spend"),
            )
            .filter(
                AdPerformance.store_id == self.store_id,
                AdPerformance.date >= start.date(),
                AdPerformance.date < end.date(),
            )
            .group_by(AdPerformance.date)
            .order_by(AdPerformance.date)
            .all()
        )
        return [(str(r.day), float(r.spend or 0)) for r in rows]
