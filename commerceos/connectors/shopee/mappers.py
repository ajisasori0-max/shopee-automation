"""Shopee-specific mappers from raw API payloads to canonical CommerceOS entities."""


from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional

from commerceos.commerce.models import (
    Ad, AdPerformance, Campaign, Inventory, Order, OrderItem, Payment, Product, Variant,
)
from commerceos.connectors.core.mapper import CanonicalEntity, Mapper
from commerceos.shared.value_objects.primitives import utc_now


def _to_decimal(value: Any) -> Decimal:
    """Convert a Shopee numeric value to Decimal, defaulting to 0."""
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def _ts_to_datetime(ts: Any) -> Optional[datetime]:
    """Convert a Shopee Unix timestamp (seconds) to UTC datetime."""
    if ts is None or ts == "":
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc)
    except (ValueError, TypeError):
        return None


class ShopeeTenantContext:
    """Tenant context required by canonical CommerceOS entities."""

    def __init__(self, organization_id: str, business_id: str, store_id: str, currency: str = "IDR"):
        self.organization_id = organization_id
        self.business_id = business_id
        self.store_id = store_id
        self.currency = currency


class ShopeeOrderMapper(Mapper):
    """Map a Shopee order detail payload to canonical ``Order`` + ``OrderItem`` entities."""

    def __init__(self, tenant: ShopeeTenantContext):
        self.tenant = tenant

    def map(self, raw_payload: Dict[str, Any]) -> List[CanonicalEntity]:
        order_sn = str(raw_payload.get("order_sn", raw_payload.get("ordersn", "")))
        if not order_sn:
            raise ValueError("Shopee order payload missing order_sn")

        items = raw_payload.get("item_list", [])
        subtotal = _to_decimal(raw_payload.get("total_amount", 0))
        shipping_cost = _to_decimal(raw_payload.get("estimated_shipping_fee", 0))
        seller_discount = _to_decimal(raw_payload.get("seller_discount", 0))
        shopee_discount = _to_decimal(raw_payload.get("shopee_discount", 0))
        discount = seller_discount + shopee_discount

        # If total_amount is missing (Shopee get_order_detail quirk), compute from items
        if subtotal == Decimal("0") and items:
            subtotal = sum(
                _to_decimal(item.get("paid_price", 0)) * int(item.get("quantity", 1))
                for item in items
            )

        # Platform fees are not present on order detail; populated from escrow/income payload.
        platform_fee = Decimal("0")
        commission = Decimal("0")
        shipping_subsidy = Decimal("0")
        tax = Decimal("0")

        total_amount = subtotal + shipping_cost - discount

        ordered_at = _ts_to_datetime(raw_payload.get("create_time"))
        if ordered_at is None:
            ordered_at = utc_now()

        paid_at = _ts_to_datetime(raw_payload.get("pay_time"))

        order_entity = CanonicalEntity(
            entity_type="order",
            external_entity_id=order_sn,
            model_class=Order,
            data={
                "marketplace_order_id": order_sn,
                "order_number": str(raw_payload.get("order_sn", order_sn)),
                "status": str(raw_payload.get("order_status", "pending")),
                "payment_status": str(raw_payload.get("payment_status", "pending")),
                "fulfillment_status": str(raw_payload.get("fulfillment_status", "")) or None,
                "currency": self.tenant.currency,
                "subtotal": subtotal,
                "shipping_cost": shipping_cost,
                "discount": discount,
                "tax": tax,
                "total_amount": total_amount,
                "platform_fee": platform_fee,
                "commission": commission,
                "shipping_subsidy": shipping_subsidy,
                "net_amount": total_amount - platform_fee - commission,
                "ordered_at": ordered_at,
                "paid_at": paid_at,
                "marketplace_metadata": raw_payload,
                "organization_id": self.tenant.organization_id,
                "business_id": self.tenant.business_id,
                "store_id": self.tenant.store_id,
            },
        )

        item_entities: List[CanonicalEntity] = []
        for item in items or []:
            item_entities.append(self._map_item(order_sn, item))

        return [order_entity] + item_entities

    def _map_item(self, order_sn: str, item: Dict[str, Any]) -> CanonicalEntity:
        quantity = int(item.get("quantity", 1))
        unit_price = _to_decimal(item.get("original_price", 0))
        paid_price = _to_decimal(item.get("paid_price", 0))
        # paid_price is the per-unit price after line-level discounts, so the line
        # total is simply paid_price * quantity. We do not double subtract discounts.
        total_price = paid_price * quantity

        return CanonicalEntity(
            entity_type="order_item",
            external_entity_id=f"{order_sn}-{item.get('item_id', '0')}",
            model_class=OrderItem,
            parent_external_id=order_sn,
            parent_field="order_id",
            data={
                "order_id": None,  # Resolved by SyncEngine from parent_external_id.
                "product_name": str(item.get("item_name", "Unknown")),
                "variant_name": str(item.get("model_name", "")),
                "sku": str(item.get("item_sku", "")),
                "quantity": quantity,
                "unit_price": unit_price,
                "total_price": total_price,
                "cost_price": _to_decimal(item.get("cost_price", 0)),
                "commission": Decimal("0"),
                "platform_fee": Decimal("0"),
                "marketplace_metadata": item,
                "organization_id": self.tenant.organization_id,
                "business_id": self.tenant.business_id,
                "store_id": self.tenant.store_id,
            },
        )


class ShopeePaymentMapper(Mapper):
    """Map a Shopee order escrow / income payload to canonical ``Payment`` entities."""

    def __init__(self, tenant: ShopeeTenantContext):
        self.tenant = tenant

    def map(self, raw_payload: Dict[str, Any]) -> List[CanonicalEntity]:
        order_sn = str(raw_payload.get("order_sn", ""))
        if not order_sn:
            raise ValueError("Shopee payment payload missing order_sn")

        income = raw_payload.get("income_details", {}) or {}
        gross_amount = _to_decimal(
            income.get("buyer_total_amount", raw_payload.get("escrow_amount", 0))
        )
        fee_amount = _to_decimal(income.get("commission", 0)) + _to_decimal(
            income.get("service_fee", 0)
        )
        net_amount = gross_amount - fee_amount

        paid_at = _ts_to_datetime(raw_payload.get("escrow_release_time"))
        if paid_at is None:
            paid_at = _ts_to_datetime(raw_payload.get("pay_time"))

        return [
            CanonicalEntity(
                entity_type="payment",
                external_entity_id=f"{order_sn}-escrow",
                model_class=Payment,
                parent_external_id=order_sn,
                parent_field="order_id",
                data={
                    "order_id": None,  # Resolved by SyncEngine from parent_external_id.
                    "marketplace_payment_id": str(raw_payload.get("payment_method", "escrow")),
                    "payment_type": "order",
                    "status": str(raw_payload.get("escrow_status", "completed")),
                    "currency": self.tenant.currency,
                    "gross_amount": gross_amount,
                    "fee_amount": fee_amount,
                    "net_amount": net_amount,
                    "paid_at": paid_at,
                    "marketplace_metadata": raw_payload,
                    "organization_id": self.tenant.organization_id,
                    "business_id": self.tenant.business_id,
                    "store_id": self.tenant.store_id,
                },
            )
        ]


class ShopeeCampaignMapper(Mapper):
    """Map Shopee campaign setting info to canonical ``Campaign`` + ``Ad`` entities.

    Shopee's ``get_product_level_campaign_setting_info`` returns one record per
    campaign. Each campaign may contain zero or more ads (product-level ads).
    """

    def __init__(self, tenant: ShopeeTenantContext):
        self.tenant = tenant

    def map(self, raw_payload: Dict[str, Any]) -> List[CanonicalEntity]:
        campaign_id = str(raw_payload.get("campaign_id", ""))
        if not campaign_id:
            raise ValueError("Shopee campaign payload missing campaign_id")

        common = raw_payload.get("common_info", {}) or {}
        campaign_name = str(common.get("ad_name", f"Campaign {campaign_id}"))
        campaign_status = str(common.get("campaign_status", "unknown")).upper()
        budget = _to_decimal(common.get("campaign_budget", 0))
        ad_type = str(common.get("ad_type", "manual"))

        campaign_entity = CanonicalEntity(
            entity_type="campaign",
            external_entity_id=campaign_id,
            model_class=Campaign,
            data={
                "marketplace_campaign_id": campaign_id,
                "name": campaign_name,
                "campaign_type": ad_type,
                "status": campaign_status,
                "budget": budget,
                "start_at": _ts_to_datetime(common.get("start_time")),
                "end_at": _ts_to_datetime(common.get("end_time")),
                "marketplace_metadata": raw_payload,
                "organization_id": self.tenant.organization_id,
                "business_id": self.tenant.business_id,
                "store_id": self.tenant.store_id,
            },
        )

        # Shopee product-level campaigns may include an item_list of ads.
        ad_entities: List[CanonicalEntity] = []
        item_list = raw_payload.get("item_list", []) or []
        for item in item_list:
            ad_id = str(item.get("ad_id", item.get("item_id", "")))
            if not ad_id:
                continue
            ad_entities.append(
                CanonicalEntity(
                    entity_type="ad",
                    external_entity_id=ad_id,
                    model_class=Ad,
                    parent_external_id=campaign_id,
                    parent_field="campaign_id",
                    data={
                        "campaign_id": None,  # Resolved by SyncEngine from parent_external_id.
                        "marketplace_ad_id": ad_id,
                        "name": str(item.get("ad_name", f"Ad {ad_id}")),
                        "ad_type": ad_type,
                        "status": str(item.get("ad_status", "unknown")).upper(),
                        "marketplace_metadata": item,
                        "organization_id": self.tenant.organization_id,
                        "business_id": self.tenant.business_id,
                        "store_id": self.tenant.store_id,
                    },
                )
            )

        return [campaign_entity] + ad_entities


class ShopeeAdsPerformanceMapper(Mapper):
    """Map Shopee daily ads performance to canonical ``AdPerformance`` entities.

    This mapper requires a provenance lookup so it can resolve marketplace
    campaign/ad IDs to canonical UUIDs before persistence.
    """

    def __init__(
        self,
        tenant: ShopeeTenantContext,
        provenance_repo: Any,
        marketplace_code: str = "shopee",
        store_id: Optional[str] = None,
    ):
        self.tenant = tenant
        self.provenance_repo = provenance_repo
        self.marketplace_code = marketplace_code
        self.store_id = store_id or tenant.store_id

    def _resolve_canonical_id(self, external_id: str) -> Optional[str]:
        entries = self.provenance_repo.get_by_external(
            marketplace_code=self.marketplace_code,
            store_id=self.store_id,
            external_entity_id=external_id,
        )
        if entries:
            return entries[0].canonical_entity_id
        return None

    def map(self, raw_payload: Dict[str, Any]) -> List[CanonicalEntity]:
        campaign_id = str(raw_payload.get("campaign_id", ""))
        ad_id = str(raw_payload.get("ad_id", ""))
        if not campaign_id or not ad_id:
            raise ValueError("Shopee ads performance payload missing campaign_id or ad_id")

        canonical_campaign_id = self._resolve_canonical_id(campaign_id)
        canonical_ad_id = self._resolve_canonical_id(ad_id)

        if canonical_campaign_id is None:
            raise ValueError(f"No canonical campaign found for marketplace campaign_id={campaign_id}")
        if canonical_ad_id is None:
            raise ValueError(f"No canonical ad found for marketplace ad_id={ad_id}")

        date_str = str(raw_payload.get("date", ""))
        if date_str:
            try:
                perf_date = datetime.strptime(date_str, "%d-%m-%Y").replace(tzinfo=timezone.utc)
            except ValueError:
                perf_date = utc_now()
        else:
            perf_date = utc_now()

        impressions = int(raw_payload.get("impression", 0))
        clicks = int(raw_payload.get("clicks", 0))
        conversions = int(raw_payload.get("direct_order", 0))
        spend = _to_decimal(raw_payload.get("expense", 0))
        revenue = _to_decimal(raw_payload.get("direct_gmv", 0))
        roas = None
        if raw_payload.get("direct_roas") is not None:
            roas = _to_decimal(raw_payload.get("direct_roas"))
        elif raw_payload.get("broad_roas") is not None:
            roas = _to_decimal(raw_payload.get("broad_roas"))
        elif raw_payload.get("roas") is not None:
            roas = _to_decimal(raw_payload.get("roas"))

        return [
            CanonicalEntity(
                entity_type="ad_performance",
                external_entity_id=f"{ad_id}-{date_str}",
                model_class=AdPerformance,
                parent_external_id=ad_id,
                parent_field="ad_id",
                data={
                    "ad_id": canonical_ad_id,
                    "campaign_id": canonical_campaign_id,
                    "date": perf_date,
                    "impressions": impressions,
                    "clicks": clicks,
                    "conversions": conversions,
                    "spend": spend,
                    "revenue": revenue,
                    "roas": roas,
                    "currency": self.tenant.currency,
                    "marketplace_metadata": raw_payload,
                    "organization_id": self.tenant.organization_id,
                    "business_id": self.tenant.business_id,
                    "store_id": self.tenant.store_id,
                },
            )
        ]


class ShopeeProductMapper(Mapper):
    """Map Shopee ``get_item_base_info`` records to canonical ``Product`` entities."""

    def __init__(self, tenant: ShopeeTenantContext):
        self.tenant = tenant

    def map(self, raw_payload: Dict[str, Any]) -> List[CanonicalEntity]:
        item_id = str(raw_payload.get("item_id", ""))
        if not item_id:
            raise ValueError("Shopee product payload missing item_id")

        return [
            CanonicalEntity(
                entity_type="product",
                external_entity_id=item_id,
                model_class=Product,
                data={
                    "name": str(raw_payload.get("item_name", f"Item {item_id}")),
                    "sku": raw_payload.get("item_sku") or f"shopee-{item_id}",
                    "description": raw_payload.get("description"),
                    "category": str(raw_payload.get("category_id", "")) or None,
                    "brand": (raw_payload.get("brand") or {}).get("original_brand_name"),
                    "selling_price": None,  # Authoritative price lives on Variants (models).
                    "is_active": str(raw_payload.get("item_status", "NORMAL")).upper() == "NORMAL",
                    "marketplace_metadata": raw_payload,
                    "organization_id": self.tenant.organization_id,
                    "business_id": self.tenant.business_id,
                    "store_id": self.tenant.store_id,
                },
            )
        ]


class ShopeeInventoryMapper(Mapper):
    """Map Shopee ``get_model_list`` records to canonical ``Variant`` + ``Inventory``.

    Each raw record is one model (variant) of an item. The variant carries the
    authoritative price (``price_info``); the child inventory record carries the
    authoritative stock (``stock_info_v2.summary_info``).

    Requires a provenance lookup to resolve the parent ``Product`` canonical UUID
    from the item_id, so the products sync must run before inventory.
    """

    def __init__(
        self,
        tenant: ShopeeTenantContext,
        provenance_repo: Any,
        marketplace_code: str = "shopee",
        store_id: Optional[str] = None,
    ):
        self.tenant = tenant
        self.provenance_repo = provenance_repo
        self.marketplace_code = marketplace_code
        self.store_id = store_id or tenant.store_id

    def _resolve_product_id(self, item_id: str) -> Optional[str]:
        entries = self.provenance_repo.get_by_external(
            marketplace_code=self.marketplace_code,
            store_id=self.store_id,
            external_entity_id=item_id,
        )
        if entries:
            return entries[0].canonical_entity_id
        return None

    def map(self, raw_payload: Dict[str, Any]) -> List[CanonicalEntity]:
        model_id = str(raw_payload.get("model_id", ""))
        item_id = str(raw_payload.get("item_id", ""))
        if not model_id:
            raise ValueError("Shopee inventory payload missing model_id")

        sku = raw_payload.get("model_sku")
        # Shopee sellers sometimes reuse the same SKU across all variants of a product.
        # Enforce uniqueness by falling back to model_id (which is unique).
        if not sku or sku in ("321D", "", "-"):
            sku = f"shopee-model-{model_id}"
        else:
            # Disambiguate in case the seller reuses SKU across models.
            sku = f"{sku}-{model_id}"
        product_id = self._resolve_product_id(item_id) if item_id else None
        if product_id is None:
            raise ValueError(f"Cannot resolve product_id for item_id={item_id} (model_id={model_id}); run products sync first")

        variant_entity = CanonicalEntity(
            entity_type="variant",
            external_entity_id=model_id,
            model_class=Variant,
            data={
                "product_id": product_id,
                "name": raw_payload.get("model_name"),
                "sku": sku,
                "selling_price": _to_decimal(raw_payload.get("current_price")),
                "cost_price": _to_decimal(raw_payload.get("original_price")),
                "is_active": str(raw_payload.get("model_status", "MODEL_STATUS_NORMAL")).upper()
                in ("MODEL_STATUS_NORMAL", "NORMAL"),
                "marketplace_metadata": {
                    "item_id": item_id,
                    "model_id": model_id,
                    "tier_index": raw_payload.get("tier_index"),
                },
                "organization_id": self.tenant.organization_id,
                "business_id": self.tenant.business_id,
                "store_id": self.tenant.store_id,
            },
        )

        inventory_entity = CanonicalEntity(
            entity_type="inventory",
            external_entity_id=model_id,
            model_class=Inventory,
            parent_external_id=model_id,
            parent_field="variant_id",
            data={
                "variant_id": None,  # Resolved by SyncEngine from parent_external_id.
                "quantity_available": int(raw_payload.get("total_available_stock") or 0),
                "quantity_reserved": int(raw_payload.get("total_reserved_stock") or 0),
                "warehouse_location": None,
                "last_synced_at": utc_now(),
                "marketplace_metadata": {
                    "item_id": item_id,
                    "seller_stock": raw_payload.get("seller_stock", []),
                },
                "organization_id": self.tenant.organization_id,
                "business_id": self.tenant.business_id,
                "store_id": self.tenant.store_id,
            },
        )

        return [variant_entity, inventory_entity]
