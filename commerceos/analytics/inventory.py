"""WP5.3 — Inventory Intelligence.

Stock + Velocity + Lead Time + Forecast → Days of Cover.

Supports:
- stockout prediction
- reorder recommendation
- safety stock
- reorder point
- supplier lead-time impact
- demand uncertainty

Integrates with the SOP engine via the LOW_STOCK SOP.
"""

from commerceos.shared.value_objects.primitives import utc_now

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from commerceos.analytics.forecasting import DemandForecastingEngine
from commerceos.commerce.models import Inventory, Order, OrderItem, Product, Variant


STORE_ID = "store-ppm-001"


@dataclass
class InventoryRecommendation:
    sku: str
    product_name: str
    available_stock: int
    daily_velocity: float
    coverage_days: float
    lead_time_days: int
    safety_stock_days: int
    days_of_cover: float
    stockout_date: Optional[str]
    recommended_reorder_quantity: int
    recommended_reorder_value: Optional[float]
    selling_price: Optional[float]
    confidence: str
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sku": self.sku,
            "product_name": self.product_name,
            "available_stock": self.available_stock,
            "daily_velocity": self.daily_velocity,
            "coverage_days": self.coverage_days,
            "lead_time_days": self.lead_time_days,
            "safety_stock_days": self.safety_stock_days,
            "days_of_cover": self.days_of_cover,
            "stockout_date": self.stockout_date,
            "recommended_reorder_quantity": self.recommended_reorder_quantity,
            "recommended_reorder_value": self.recommended_reorder_value,
            "selling_price": self.selling_price,
            "confidence": self.confidence,
            "notes": self.notes,
        }


class InventoryIntelligenceEngine:
    """Compute inventory intelligence for a store."""

    DEFAULT_LEAD_TIME_DAYS = 7
    SAFETY_STOCK_DAYS = 7

    def __init__(self, session: Session, store_id: str = STORE_ID):
        self.session = session
        self.store_id = store_id
        self.forecaster = DemandForecastingEngine(session, store_id)

    def recommend(
        self,
        sku: Optional[str] = None,
        days_of_history: int = 30,
    ) -> Dict[str, Any]:
        """Return reorder recommendations for all SKUs or a single SKU."""
        end = utc_now()
        start = end - timedelta(days=days_of_history)

        query = (
            self.session.query(
                Inventory.quantity_available,
                Inventory.quantity_reserved,
                Variant.id.label("variant_id"),
                Variant.sku,
                Variant.selling_price,
                Product.name.label("product_name"),
            )
            .join(Variant, Inventory.variant_id == Variant.id)
            .join(Product, Variant.product_id == Product.id)
            .filter(Inventory.store_id == self.store_id)
        )
        if sku:
            query = query.filter(Variant.sku == sku)
        rows = query.all()

        # Compute velocity per SKU over the historical window.
        velocity_rows = (
            self.session.query(
                OrderItem.sku,
                func.sum(OrderItem.quantity).label("units"),
            )
            .join(Order, OrderItem.order_id == Order.id)
            .filter(
                Order.store_id == self.store_id,
                Order.ordered_at >= start,
                Order.status.notin_(["cancelled"]),
            )
            .group_by(OrderItem.sku)
            .all()
        )
        velocity_by_sku = {r.sku: int(r.units or 0) / days_of_history for r in velocity_rows if r.sku}

        recommendations = []
        for row in rows:
            available = row.quantity_available or 0
            sku_value = row.sku or f"variant-{row.variant_id[:8]}"
            velocity = velocity_by_sku.get(sku_value, 0.0)
            coverage = (available / velocity) if velocity > 0 else 999.0

            lead_time = self.DEFAULT_LEAD_TIME_DAYS
            safety_stock = self.SAFETY_STOCK_DAYS
            days_of_cover = coverage + lead_time + safety_stock

            # Stockout date: when current stock runs out at current velocity.
            stockout_date = None
            if velocity > 0:
                stockout_dt = utc_now() + timedelta(days=coverage)
                stockout_date = stockout_dt.date().isoformat()

            # Reorder point: stock needed to cover lead time + safety stock.
            reorder_point = int(velocity * (lead_time + safety_stock))
            recommended_qty = max(0, reorder_point - available)
            selling_price = float(row.selling_price) if row.selling_price else None
            recommended_value = (recommended_qty * selling_price) if selling_price and recommended_qty > 0 else None

            notes = []
            if velocity == 0:
                notes.append("No recent sales velocity; demand forecast unavailable.")
            if recommended_qty > 0:
                notes.append(f"Stock below reorder point ({reorder_point}).")
            else:
                notes.append("Stock above reorder point.")

            recommendations.append(InventoryRecommendation(
                sku=sku_value,
                product_name=row.product_name or "Unknown",
                available_stock=available,
                daily_velocity=round(velocity, 2),
                coverage_days=round(coverage, 1),
                lead_time_days=lead_time,
                safety_stock_days=safety_stock,
                days_of_cover=round(days_of_cover, 1),
                stockout_date=stockout_date,
                recommended_reorder_quantity=recommended_qty,
                recommended_reorder_value=round(recommended_value, 2) if recommended_value else None,
                selling_price=selling_price,
                confidence="low" if velocity == 0 else "medium",
                notes=notes,
            ))

        return {
            "store_id": self.store_id,
            "generated_at": utc_now().isoformat(),
            "history_days": days_of_history,
            "recommendations": [r.to_dict() for r in recommendations],
        }

    def stockout_risk(self, days_ahead: int = 14) -> Dict[str, Any]:
        """Return SKUs projected to stock out within the lookahead window."""
        recommendations = self.recommend()["recommendations"]
        at_risk = [r for r in recommendations if r["coverage_days"] < days_ahead]
        return {
            "store_id": self.store_id,
            "lookahead_days": days_ahead,
            "at_risk_count": len(at_risk),
            "at_risk_skus": at_risk,
        }
