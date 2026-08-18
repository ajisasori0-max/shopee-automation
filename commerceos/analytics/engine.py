"""WP5.1 — Advanced Analytics.

Business analytics including:
- SKU profitability
- Campaign profitability
- Contribution margin
- Cohort analysis (where data supports)
- Customer/repeat behavior (where data exists)
- Revenue/margin decomposition
- Operational performance analysis

Data-honest: unavailable dimensions are reported as missing, not fabricated.
"""

from commerceos.shared.value_objects.primitives import utc_now

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from commerceos.commerce.models import Ad, AdPerformance, Campaign, Order, OrderItem, Payment, Product, Variant


STORE_ID = "store-ppm-001"


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@dataclass
class SKUProfitability:
    sku: str
    product_name: str
    units_sold: int
    gross_revenue: float
    discounts: float
    net_revenue: float
    marketplace_fees: float
    advertising_cost: float
    cogs: Optional[float]
    contribution_margin: float
    contribution_margin_pct: Optional[float]
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sku": self.sku,
            "product_name": self.product_name,
            "units_sold": self.units_sold,
            "gross_revenue": self.gross_revenue,
            "discounts": self.discounts,
            "net_revenue": self.net_revenue,
            "marketplace_fees": self.marketplace_fees,
            "advertising_cost": self.advertising_cost,
            "cogs": self.cogs,
            "contribution_margin": self.contribution_margin,
            "contribution_margin_pct": self.contribution_margin_pct,
            "notes": self.notes,
        }


@dataclass
class CampaignProfitability:
    campaign_id: str
    campaign_name: str
    spend: float
    revenue: float
    roas: float
    clicks: int
    conversions: int
    cpa: Optional[float]
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "campaign_name": self.campaign_name,
            "spend": self.spend,
            "revenue": self.revenue,
            "roas": self.roas,
            "clicks": self.clicks,
            "conversions": self.conversions,
            "cpa": self.cpa,
            "notes": self.notes,
        }


class AdvancedAnalyticsEngine:
    """Compute business analytics from canonical CommerceOS tables."""

    def __init__(self, session: Session, store_id: str = STORE_ID):
        self.session = session
        self.store_id = store_id

    def sku_profitability(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Return SKU-level profitability. COGS is reported as missing if unavailable."""
        end = end or utc_now()
        start = start or (end - timedelta(days=30))

        order_items = (
            self.session.query(
                OrderItem.sku,
                Product.name.label("product_name"),
                func.sum(OrderItem.quantity).label("units_sold"),
                func.sum(OrderItem.total_price).label("gross_revenue"),
                func.sum(Order.discount).label("discounts"),
            )
            .join(Order, OrderItem.order_id == Order.id)
            .outerjoin(Variant, OrderItem.variant_id == Variant.id)
            .outerjoin(Product, Variant.product_id == Product.id)
            .filter(
                Order.store_id == self.store_id,
                Order.ordered_at >= start,
                Order.ordered_at < end,
                Order.status.notin_(["cancelled"]),
            )
            .group_by(OrderItem.sku, Product.name)
            .all()
        )

        # Marketplace fees per SKU from payments (approximate by order share)
        payments = float(
            self.session.query(func.sum(Payment.fee_amount).label("total_fees"))
            .filter(
                Payment.store_id == self.store_id,
                Payment.paid_at >= start,
                Payment.paid_at < end,
            )
            .scalar() or 0
        )

        total_revenue = sum(_safe_float(r.gross_revenue) or 0.0 for r in order_items)
        fee_ratio = (payments / total_revenue) if total_revenue else 0.0

        # Advertising cost per SKU: proportional to SKU revenue (approximation)
        ad_spend = float(
            self.session.query(func.sum(AdPerformance.spend).label("total_spend"))
            .filter(
                AdPerformance.store_id == self.store_id,
                AdPerformance.date >= start,
                AdPerformance.date < end,
            )
            .scalar()
            or 0
        )
        ad_ratio = (ad_spend / total_revenue) if total_revenue else 0.0

        results = []
        for row in order_items:
            gross = _safe_float(row.gross_revenue) or 0.0
            discount = _safe_float(row.discounts) or 0.0
            net = gross - discount
            fees = gross * fee_ratio
            ads = gross * ad_ratio
            cogs = None  # COGS not available in canonical tables
            contribution = net - fees - ads
            margin_pct = (contribution / net * 100) if net else None
            notes = []
            if cogs is None:
                notes.append("COGS unavailable; contribution margin is before COGS")
            results.append(SKUProfitability(
                sku=row.sku,
                product_name=row.product_name or "Unknown",
                units_sold=int(row.units_sold or 0),
                gross_revenue=gross,
                discounts=discount,
                net_revenue=net,
                marketplace_fees=fees,
                advertising_cost=ads,
                cogs=cogs,
                contribution_margin=contribution,
                contribution_margin_pct=margin_pct,
                notes=notes,
            ))

        return {
            "period": {"start": start.isoformat(), "end": end.isoformat()},
            "sku_count": len(results),
            "total_revenue": total_revenue,
            "total_marketplace_fees": payments,
            "total_advertising": ad_spend,
            "cogs_available": False,
            "skus": [r.to_dict() for r in sorted(results, key=lambda x: x.contribution_margin, reverse=True)],
        }

    def campaign_profitability(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Return campaign-level ad profitability."""
        end = end or utc_now()
        start = start or (end - timedelta(days=30))

        perf = (
            self.session.query(
                AdPerformance.campaign_id,
                Campaign.name.label("campaign_name"),
                func.sum(AdPerformance.spend).label("spend"),
                func.sum(AdPerformance.revenue).label("revenue"),
                func.sum(AdPerformance.clicks).label("clicks"),
                func.sum(AdPerformance.conversions).label("conversions"),
            )
            .outerjoin(Campaign, AdPerformance.campaign_id == Campaign.id)
            .filter(
                AdPerformance.store_id == self.store_id,
                AdPerformance.date >= start,
                AdPerformance.date < end,
            )
            .group_by(AdPerformance.campaign_id, Campaign.name)
            .all()
        )

        results = []
        for row in perf:
            spend = _safe_float(row.spend) or 0.0
            revenue = _safe_float(row.revenue) or 0.0
            roas = (revenue / spend) if spend else 0.0
            conversions = int(row.conversions or 0)
            cpa = (spend / conversions) if conversions else None
            results.append(CampaignProfitability(
                campaign_id=row.campaign_id,
                campaign_name=row.campaign_name or "Unknown",
                spend=spend,
                revenue=revenue,
                roas=roas,
                clicks=int(row.clicks or 0),
                conversions=conversions,
                cpa=cpa,
            ))

        return {
            "period": {"start": start.isoformat(), "end": end.isoformat()},
            "campaign_count": len(results),
            "total_spend": sum(r.spend for r in results),
            "total_revenue": sum(r.revenue for r in results),
            "overall_roas": (sum(r.revenue for r in results) / sum(r.spend for r in results)) if sum(r.spend for r in results) else 0.0,
            "campaigns": [r.to_dict() for r in sorted(results, key=lambda x: x.roas, reverse=True)],
        }

    def revenue_decomposition(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Decompose revenue into orders, AOV, and SKU mix."""
        end = end or utc_now()
        start = start or (end - timedelta(days=30))

        order_stats = (
            self.session.query(
                func.count(Order.id).label("order_count"),
                func.sum(Order.total_amount).label("revenue"),
                func.sum(Order.discount).label("discounts"),
            )
            .filter(
                Order.store_id == self.store_id,
                Order.ordered_at >= start,
                Order.ordered_at < end,
                Order.status.notin_(["cancelled"]),
            )
            .first()
        )
        orders = int(order_stats.order_count or 0) if order_stats else 0
        revenue = _safe_float(order_stats.revenue) or 0.0 if order_stats else 0.0
        discounts = _safe_float(order_stats.discounts) or 0.0 if order_stats else 0.0

        return {
            "period": {"start": start.isoformat(), "end": end.isoformat()},
            "orders": orders,
            "gross_revenue": revenue,
            "discounts": discounts,
            "net_revenue": revenue - discounts,
            "aov": (revenue / orders) if orders else 0.0,
            "notes": ["Revenue decomposition uses order totals and discounts only."],
        }

    def customer_repeat_behavior(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Customer repeat behavior. Shopee data lacks customer identity; report unavailable."""
        return {
            "available": False,
            "reason": "Customer identity and order history are not available in the connected Shopee data model.",
            "metrics": ["repeat_customer_rate", "customer_lifetime_value", "cohort_retention"],
            "notes": ["Enable customer-level data ingestion to compute these metrics."],
        }

    def cohort_analysis(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Cohort analysis. Unavailable without customer identity."""
        return self.customer_repeat_behavior(start, end)

    def operational_performance(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Operational performance: order fulfillment, payment status, inventory."""
        end = end or utc_now()
        start = start or (end - timedelta(days=30))

        order_counts = (
            self.session.query(
                Order.status,
                func.count(Order.id).label("count"),
            )
            .filter(
                Order.store_id == self.store_id,
                Order.ordered_at >= start,
                Order.ordered_at < end,
            )
            .group_by(Order.status)
            .all()
        )

        payment_counts = (
            self.session.query(
                Payment.status,
                func.count(Payment.id).label("count"),
            )
            .filter(
                Payment.store_id == self.store_id,
                Payment.paid_at >= start,
                Payment.paid_at < end,
            )
            .group_by(Payment.status)
            .all()
        )

        return {
            "period": {"start": start.isoformat(), "end": end.isoformat()},
            "orders_by_status": {r.status: int(r.count) for r in order_counts},
            "payments_by_status": {r.status: int(r.count) for r in payment_counts},
            "notes": ["Operational performance is based on canonical order and payment status counts."],
        }

    def summary(self, days: int = 30) -> Dict[str, Any]:
        """Return a consolidated analytics summary."""
        end = utc_now()
        start = end - timedelta(days=days)
        return {
            "generated_at": utc_now().isoformat(),
            "period_days": days,
            "sku_profitability": self.sku_profitability(start, end),
            "campaign_profitability": self.campaign_profitability(start, end),
            "revenue_decomposition": self.revenue_decomposition(start, end),
            "customer_repeat_behavior": self.customer_repeat_behavior(start, end),
            "operational_performance": self.operational_performance(start, end),
        }
