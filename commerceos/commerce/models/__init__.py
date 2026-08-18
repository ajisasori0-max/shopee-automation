from commerceos.shared.value_objects.primitives import utc_now
from typing import Optional, List
from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    String,
    Text,
    Numeric,
    Integer,
    Boolean,
    ForeignKey,
    JSON,
    DateTime,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from commerceos.platform.database.models import Base, TimestampMixin, TenantMixin, new_uuid


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="Asia/Jakarta")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Business(Base, TimestampMixin):
    __tablename__ = "businesses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="Asia/Jakarta")
    default_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="IDR")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    organization: Mapped["Organization"] = relationship("Organization")


class Marketplace(Base, TimestampMixin):
    __tablename__ = "marketplaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Store(Base, TimestampMixin, TenantMixin):
    __tablename__ = "stores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    business_id: Mapped[str] = mapped_column(String(36), ForeignKey("businesses.id"), nullable=False)
    marketplace_id: Mapped[str] = mapped_column(String(36), ForeignKey("marketplaces.id"), nullable=False)
    marketplace_store_id: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    auth_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    business: Mapped["Business"] = relationship("Business")
    marketplace: Mapped["Marketplace"] = relationship("Marketplace")

    __table_args__ = (
        UniqueConstraint("business_id", "marketplace_id", "marketplace_store_id", name="uq_store_marketplace_identifier"),
    )


class Product(Base, TimestampMixin, TenantMixin):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    sku: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    brand: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    cost_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    selling_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    marketplace_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_products_tenant_sku", "organization_id", "business_id", "store_id", "sku"),
    )


class Variant(Base, TimestampMixin, TenantMixin):
    __tablename__ = "variants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products.id"), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sku: Mapped[str] = mapped_column(String(255), nullable=False)
    barcode: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    cost_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    selling_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    marketplace_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    product: Mapped["Product"] = relationship("Product")

    __table_args__ = (
        UniqueConstraint("organization_id", "business_id", "store_id", "sku", name="uq_variant_sku_per_store"),
    )


class Inventory(Base, TimestampMixin, TenantMixin):
    __tablename__ = "inventory"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    variant_id: Mapped[str] = mapped_column(String(36), ForeignKey("variants.id"), nullable=False)
    quantity_available: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quantity_reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warehouse_location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    marketplace_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    variant: Mapped["Variant"] = relationship("Variant")

    __table_args__ = (
        Index("ix_inventory_tenant_variant", "organization_id", "business_id", "store_id", "variant_id"),
    )


class Order(Base, TimestampMixin, TenantMixin):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    marketplace_order_id: Mapped[str] = mapped_column(String(255), nullable=False)
    order_number: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    payment_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    fulfillment_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="IDR")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    shipping_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    discount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    tax: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    platform_fee: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    commission: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    shipping_subsidy: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    net_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    ordered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    marketplace_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="order")
    payments: Mapped[List["Payment"]] = relationship("Payment", back_populates="order")

    __table_args__ = (
        UniqueConstraint("organization_id", "business_id", "store_id", "marketplace_order_id", name="uq_order_marketplace_id"),
        Index("ix_orders_status_ordered_at", "status", "ordered_at"),
    )


class OrderItem(Base, TimestampMixin, TenantMixin):
    __tablename__ = "order_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    order_id: Mapped[str] = mapped_column(String(36), ForeignKey("orders.id"), nullable=False)
    variant_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("variants.id"), nullable=True)
    product_name: Mapped[str] = mapped_column(String(500), nullable=False)
    variant_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sku: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    total_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    cost_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    commission: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    platform_fee: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    marketplace_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    order: Mapped["Order"] = relationship("Order", back_populates="items")
    variant: Mapped[Optional["Variant"]] = relationship("Variant")


class Payment(Base, TimestampMixin, TenantMixin):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    order_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("orders.id"), nullable=True)
    marketplace_payment_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    payment_type: Mapped[str] = mapped_column(String(50), nullable=False, default="order")
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="IDR")
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    fee_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    net_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    marketplace_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    order: Mapped[Optional["Order"]] = relationship("Order", back_populates="payments")

    __table_args__ = (
        Index("ix_payments_order_id", "order_id"),
    )


class Expense(Base, TimestampMixin, TenantMixin):
    __tablename__ = "expenses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="IDR")
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    incurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: utc_now())
    marketplace_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_expenses_category_incurred_at", "category", "incurred_at"),
    )


class Revenue(Base, TimestampMixin, TenantMixin):
    __tablename__ = "revenue"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    order_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("orders.id"), nullable=True)
    payment_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("payments.id"), nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="sale")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="IDR")
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    fee_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    net_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    recognized_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    marketplace_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_revenue_recognized_at", "recognized_at"),
    )


class Campaign(Base, TimestampMixin, TenantMixin):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    marketplace_campaign_id: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    campaign_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    budget: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    start_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    end_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    marketplace_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    ads: Mapped[List["Ad"]] = relationship("Ad", back_populates="campaign")

    __table_args__ = (
        UniqueConstraint("organization_id", "business_id", "store_id", "marketplace_campaign_id", name="uq_campaign_marketplace_id"),
    )


class Ad(Base, TimestampMixin, TenantMixin):
    __tablename__ = "ads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    campaign_id: Mapped[str] = mapped_column(String(36), ForeignKey("campaigns.id"), nullable=False)
    marketplace_ad_id: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    ad_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    marketplace_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="ads")
    performances: Mapped[List["AdPerformance"]] = relationship("AdPerformance", back_populates="ad")

    __table_args__ = (
        UniqueConstraint("organization_id", "business_id", "store_id", "marketplace_ad_id", name="uq_ad_marketplace_id"),
    )


class AdPerformance(Base, TimestampMixin, TenantMixin):
    __tablename__ = "ad_performances"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    ad_id: Mapped[str] = mapped_column(String(36), ForeignKey("ads.id"), nullable=False)
    campaign_id: Mapped[str] = mapped_column(String(36), ForeignKey("campaigns.id"), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conversions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    spend: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    revenue: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    roas: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="IDR")
    marketplace_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    ad: Mapped["Ad"] = relationship("Ad", back_populates="performances")
    campaign: Mapped["Campaign"] = relationship("Campaign")

    __table_args__ = (
        UniqueConstraint("ad_id", "date", name="uq_ad_performance_date"),
        Index("ix_ad_performance_date", "date"),
    )


class BusinessRule(Base, TimestampMixin, TenantMixin):
    __tablename__ = "business_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    condition: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("organization_id", "business_id", "store_id", "code", name="uq_business_rule_code"),
    )


class RuleExecution(Base, TimestampMixin, TenantMixin):
    __tablename__ = "rule_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    rule_id: Mapped[str] = mapped_column(String(36), ForeignKey("business_rules.id"), nullable=False)
    triggered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    inputs: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    outputs: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: utc_now())

    rule: Mapped["BusinessRule"] = relationship("BusinessRule")


class KPI(Base, TimestampMixin, TenantMixin):
    __tablename__ = "kpis"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    formula: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=Decimal("1.0"))
    freshness: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    marketplace_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint("organization_id", "business_id", "store_id", "code", "freshness", name="uq_kpi_code"),
    )


class KPIHistory(Base, TimestampMixin, TenantMixin):
    __tablename__ = "kpi_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    kpi_id: Mapped[str] = mapped_column(String(36), ForeignKey("kpis.id"), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=Decimal("1.0"))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: utc_now())
    marketplace_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    kpi: Mapped["KPI"] = relationship("KPI")

    __table_args__ = (
        Index("ix_kpi_history_recorded_at", "recorded_at"),
    )


class CommerceState(Base, TimestampMixin, TenantMixin):
    __tablename__ = "commerce_states"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    version: Mapped[str] = mapped_column(String(20), nullable=False, default="1")
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    data_quality_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=Decimal("1.0"))
    confidence_level: Mapped[str] = mapped_column(String(20), nullable=False, default="high")
    sources_fresh: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    sources_stale: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    alerts: Mapped[List[dict]] = mapped_column(JSON, nullable=False, default=list)
    risks: Mapped[List[dict]] = mapped_column(JSON, nullable=False, default=list)
    opportunities: Mapped[List[dict]] = mapped_column(JSON, nullable=False, default=list)
    anomalies: Mapped[List[dict]] = mapped_column(JSON, nullable=False, default=list)
    todays_focus: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    last_sync: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    data_quality: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    marketplace_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_commerce_states_generated_at", "created_at"),
    )


class DataQualityEvent(Base, TimestampMixin, TenantMixin):
    __tablename__ = "data_quality_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    issue_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_data_quality_events_severity", "severity"),
    )


class ReconciliationEvent(Base, TimestampMixin, TenantMixin):
    __tablename__ = "reconciliation_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    source_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    computed_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    difference: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    tolerance: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_reconciliation_events_status", "status"),
    )
