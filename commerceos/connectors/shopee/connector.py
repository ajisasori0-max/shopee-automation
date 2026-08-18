"""Shopee marketplace connector for the CommerceOS ingestion engine."""


import json
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from commerceos.commerce.models import Order, OrderItem, Payment
from commerceos.connectors.core.errors import ConnectorAuthError
from commerceos.connectors.core.interfaces import (
    ConnectorAuth,
    ConnectorHealth,
    ConnectorResult,
    MarketplaceConnector,
    SyncMode,
)
from commerceos.connectors.shopee.auth import ShopeeAuth
from commerceos.connectors.shopee.client import ShopeeApiClient
from commerceos.connectors.shopee.mappers import (
    ShopeeAdsPerformanceMapper,
    ShopeeCampaignMapper,
    ShopeeOrderMapper,
    ShopeePaymentMapper,
    ShopeeTenantContext,
)
from commerceos.platform.secrets.manager import SecretManager
from commerceos.shared.value_objects.primitives import utc_now


class ShopeeConnector(MarketplaceConnector):
    """Connector that fetches orders, payments, products, inventory, and ads
    from Shopee Open API v2.

    The connector is built around a ``ShopeeApiClient`` which can be injected for
    testing. In production it is constructed from credentials stored in the
    ``SecretManager`` under the ``shopee/{store_id}/`` namespace.
    """

    VERSION = "1.0.0"
    DEFAULT_PAGE_SIZE = 100

    def __init__(
        self,
        store_id: str,
        tenant: ShopeeTenantContext,
        secret_manager: Optional[SecretManager] = None,
        api_client: Optional[Any] = None,
        sandbox: bool = False,
    ):
        self.store_id = store_id
        self.tenant = tenant
        self._auth = ShopeeAuth(store_id=store_id, secret_manager=secret_manager)
        self._api_client = api_client
        self._sandbox = sandbox

    @property
    def _client(self) -> Any:
        if self._api_client is None:
            self._api_client = self._build_api_client(self._sandbox)
        return self._api_client

    def _build_api_client(self, sandbox: bool) -> Any:
        creds = self._auth.get_credentials()
        partner_id = creds.get("partner_id")
        partner_key = creds.get("partner_key")
        access_token = creds.get("access_token")
        if not partner_id or not partner_key:
            raise ConnectorAuthError("Shopee partner_id and partner_key are required")
        return ShopeeApiClient(
            partner_id=int(partner_id),
            partner_key=partner_key,
            shop_id=int(self.store_id),
            access_token=access_token,
            sandbox=sandbox,
        )

    @property
    def marketplace_code(self) -> str:
        return "shopee"

    @property
    def name(self) -> str:
        return "Shopee"

    @property
    def version(self) -> str:
        return self.VERSION

    @property
    def auth(self) -> ConnectorAuth:
        return self._auth

    def health(self) -> ConnectorHealth:
        if not self._auth.is_authenticated:
            return ConnectorHealth(
                authenticated=False,
                api_available=False,
                status="unauthenticated",
                errors=["Missing partner_id, partner_key, or shop_id"],
            )

        result = self._client.get_shop_info()
        if not result["ok"]:
            return ConnectorHealth(
                authenticated=True,
                api_available=False,
                status="unhealthy",
                errors=[result.get("error") or "Shopee API returned an error"],
            )

        return ConnectorHealth(
            authenticated=True,
            api_available=True,
            status="healthy",
        )

    def fetch_orders(
        self,
        sync_mode: SyncMode = SyncMode.INCREMENTAL,
        cursor: Optional[str] = None,
        **kwargs: Any,
    ) -> ConnectorResult:
        """Fetch order detail payloads from Shopee.

        The cursor is a JSON string containing ``time_to`` and ``page_cursor``.
        """
        try:
            time_from, time_to, page_cursor = self._resolve_time_range(sync_mode, cursor)
            result = self._client.get_order_list(
                time_from=time_from,
                time_to=time_to,
                time_range_field="update_time",
                page_size=self.DEFAULT_PAGE_SIZE,
                cursor=page_cursor,
                order_status="ALL",
            )
            if not result["ok"]:
                return ConnectorResult.failed(
                    message=result.get("error") or "Failed to fetch Shopee order list",
                    metadata={"status_code": result.get("status_code")},
                )

            response = result.get("response", {})
            order_list = response.get("order_list", [])
            order_sn_list = [o.get("order_sn") for o in order_list if o.get("order_sn")]
            next_cursor = response.get("next_cursor")
            more = response.get("more", False)

            if not order_sn_list:
                return ConnectorResult.ok(
                    data=[],
                    metadata={
                        "cursor": self._encode_cursor(time_to, next_cursor) if next_cursor else None,
                        "source_timestamp": utc_now().isoformat(),
                    },
                )

            detail_result = self._client.get_order_detail(
                order_sn_list=",".join(order_sn_list)
            )
            if not detail_result["ok"]:
                return ConnectorResult.failed(
                    message=detail_result.get("error") or "Failed to fetch Shopee order details",
                    metadata={"status_code": detail_result.get("status_code")},
                )

            order_details = detail_result.get("response", {}).get("order_list", [])
            return ConnectorResult.ok(
                data=order_details,
                metadata={
                    "cursor": self._encode_cursor(time_to, next_cursor) if more or next_cursor else None,
                    "source_timestamp": utc_now().isoformat(),
                    "order_count": len(order_details),
                },
            )
        except Exception as exc:
            return ConnectorResult.from_exception(exc)

    def fetch_payments(
        self,
        sync_mode: SyncMode = SyncMode.INCREMENTAL,
        cursor: Optional[str] = None,
        **kwargs: Any,
    ) -> ConnectorResult:
        """Fetch payment (escrow) payloads from Shopee.

        Uses order-level deterministic fallback when the escrow endpoint is
        unavailable. The fallback computes payment data from the order detail
        payload itself, marked with reduced confidence.
        """
        try:
            time_from, time_to, page_cursor = self._resolve_time_range(sync_mode, cursor)
            result = self._client.get_order_list(
                time_from=time_from,
                time_to=time_to,
                time_range_field="update_time",
                page_size=self.DEFAULT_PAGE_SIZE,
                cursor=page_cursor,
                order_status="ALL",
            )
            if not result["ok"]:
                return ConnectorResult.failed(
                    message=result.get("error") or "Failed to fetch Shopee order list",
                    metadata={"status_code": result.get("status_code")},
                )

            response = result.get("response", {})
            order_list = response.get("order_list", [])
            order_sn_list = [o.get("order_sn") for o in order_list if o.get("order_sn")]
            next_cursor = response.get("next_cursor")
            more = response.get("more", False)

            if not order_sn_list:
                return ConnectorResult.ok(
                    data=[],
                    metadata={
                        "cursor": self._encode_cursor(time_to, next_cursor) if next_cursor else None,
                        "source_timestamp": utc_now().isoformat(),
                    },
                )

            # Try escrow endpoint first
            escrow_details: List[Dict[str, Any]] = []
            escrow_failed = False
            for i in range(0, len(order_sn_list), 50):
                batch = ",".join(order_sn_list[i : i + 50])
                income_result = self._client.get_order_income(batch)
                if not income_result["ok"]:
                    escrow_failed = True
                    break
                escrow_details.extend(
                    income_result.get("response", {}).get("order_income_list", [])
                )

            # Fallback: deterministic order-level payment calculation
            if escrow_failed or not escrow_details:
                detail_result = self._client.get_order_detail(
                    order_sn_list=",".join(order_sn_list)
                )
                if not detail_result["ok"]:
                    return ConnectorResult.failed(
                        message=detail_result.get("error") or "Failed to fetch order details for payment fallback",
                        metadata={"status_code": detail_result.get("status_code")},
                    )
                order_details = detail_result.get("response", {}).get("order_list", [])
                for order in order_details:
                    escrow_details.append(self._order_to_payment_fallback(order))

            return ConnectorResult.ok(
                data=escrow_details,
                metadata={
                    "cursor": self._encode_cursor(time_to, next_cursor) if more or next_cursor else None,
                    "source_timestamp": utc_now().isoformat(),
                    "payment_count": len(escrow_details),
                    "fallback_used": escrow_failed,
                    "confidence": "reduced" if escrow_failed else "high",
                },
            )
        except Exception as exc:
            return ConnectorResult.from_exception(exc)

    def _order_to_payment_fallback(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Compute a payment-like payload from order detail when escrow is unavailable.

        This is a deterministic fallback with reduced confidence. It estimates
        payment amounts from the order total, shipping, and discount fields.
        """
        # Compute total from items if total_amount is missing
        total = order.get("total_amount")
        if total is None:
            total = 0
            for item in order.get("item_list", []):
                price = item.get("item_price", 0) or item.get("discounted_price", 0) or 0
                qty = item.get("model_quantity_purchased", 1) or 1
                total += int(price * qty)
        else:
            total = int(total)
        
        shipping = order.get("estimated_shipping_fee", 0) or 0
        seller_discount = order.get("seller_discount", 0) or 0
        shopee_discount = order.get("shopee_discount", 0) or 0
        discount = seller_discount + shopee_discount

        # Estimate: Shopee fee ~5% + service fee ~1% (placeholder until real data)
        estimated_fees = int(total * 0.06)
        net = total - estimated_fees

        return {
            "order_sn": order.get("order_sn"),
            "payment_method": "fallback",
            "escrow_status": order.get("payment_status", "pending"),
            "escrow_amount": total,
            "escrow_release_time": order.get("pay_time"),
            "income_details": {
                "buyer_total_amount": total,
                "commission": estimated_fees,
                "service_fee": 0,
                "seller_shipping_discount": 0,
                "voucher_amount": discount,
                "items_total": total - shipping + discount,
                "shipping_fee": shipping,
            },
            "_fallback": True,
            "_confidence": "reduced",
        }

    def fetch_products(
        self,
        sync_mode: SyncMode = SyncMode.INCREMENTAL,
        cursor: Optional[str] = None,
        **kwargs: Any,
    ) -> ConnectorResult:
        """Fetch product list from Shopee.

        Uses /api/v2/product/get_item_list for IDs, then
        /api/v2/product/get_item_base_info for details.
        """
        try:
            list_result = self._client._call(
                "GET",
                "/api/v2/product/get_item_list",
                params={"offset": 0, "page_size": 100, "item_status": "NORMAL"},
            )
            if not list_result["ok"]:
                return ConnectorResult.failed(
                    message=list_result.get("error") or "Failed to fetch product list",
                    metadata={"status_code": list_result.get("status_code")},
                )

            # get_item_list returns items under "item" key (not "item_list")
            item_list = list_result.get("response", {}).get("item", [])
            item_ids = [str(i.get("item_id")) for i in item_list if i.get("item_id")]

            if not item_ids:
                return ConnectorResult.ok(
                    data=[],
                    metadata={"source_timestamp": utc_now().isoformat()},
                )

            # Fetch details in batches of 50
            products: List[Dict[str, Any]] = []
            for i in range(0, len(item_ids), 50):
                batch = ",".join(item_ids[i : i + 50])
                detail_result = self._client._call(
                    "GET",
                    "/api/v2/product/get_item_base_info",
                    params={"item_id_list": batch},
                )
                if detail_result["ok"]:
                    products.extend(
                        detail_result.get("response", {}).get("item_list", [])
                    )

            return ConnectorResult.ok(
                data=products,
                metadata={
                    "source_timestamp": utc_now().isoformat(),
                    "product_count": len(products),
                },
            )
        except Exception as exc:
            return ConnectorResult.from_exception(exc)

    def fetch_inventory(
        self,
        sync_mode: SyncMode = SyncMode.INCREMENTAL,
        cursor: Optional[str] = None,
        **kwargs: Any,
    ) -> ConnectorResult:
        """Fetch inventory/stock from Shopee.

        Uses the same product endpoints; stock is included in item base info.
        """
        try:
            list_result = self._client._call(
                "GET",
                "/api/v2/product/get_item_list",
                params={"offset": 0, "page_size": 100, "item_status": "NORMAL"},
            )
            if not list_result["ok"]:
                return ConnectorResult.failed(
                    message=list_result.get("error") or "Failed to fetch product list for inventory",
                    metadata={"status_code": list_result.get("status_code")},
                )

            # get_item_list returns items under "item" key (not "item_list")
            item_list = list_result.get("response", {}).get("item", [])
            item_ids = [str(i.get("item_id")) for i in item_list if i.get("item_id")]

            if not item_ids:
                return ConnectorResult.ok(
                    data=[],
                    metadata={"source_timestamp": utc_now().isoformat()},
                )

            inventory: List[Dict[str, Any]] = []
            # Stock and price live in get_model_list (per item), not item_base_info.
            # stock_info_v2.seller_stock[].stock is the authoritative available stock.
            for item_id in item_ids:
                model_result = self._client._call(
                    "GET",
                    "/api/v2/product/get_model_list",
                    params={"item_id": item_id},
                )
                if not model_result["ok"]:
                    continue
                response = model_result.get("response", {})
                models = response.get("model", [])
                for m in models:
                    stock_v2 = m.get("stock_info_v2") or {}
                    summary = stock_v2.get("summary_info") or {}
                    price_info = (m.get("price_info") or [{}])[0]
                    inventory.append({
                        "item_id": item_id,
                        "model_id": m.get("model_id"),
                        "model_name": m.get("model_name"),
                        "model_sku": m.get("model_sku"),
                        "model_status": m.get("model_status"),
                        "current_price": price_info.get("current_price"),
                        "original_price": price_info.get("original_price"),
                        "currency": price_info.get("currency", "IDR"),
                        "total_available_stock": summary.get("total_available_stock", 0),
                        "total_reserved_stock": summary.get("total_reserved_stock", 0),
                        "seller_stock": stock_v2.get("seller_stock", []),
                        "tier_index": m.get("tier_index"),
                    })

            return ConnectorResult.ok(
                data=inventory,
                metadata={
                    "source_timestamp": utc_now().isoformat(),
                    "inventory_count": len(inventory),
                },
            )
        except Exception as exc:
            return ConnectorResult.from_exception(exc)

    def fetch_ads(
        self,
        sync_mode: SyncMode = SyncMode.INCREMENTAL,
        cursor: Optional[str] = None,
        **kwargs: Any,
    ) -> ConnectorResult:
        """Convenience method that fetches both campaigns and ad performance.

        This is not used by the SyncEngine (which syncs one entity type at a time);
        prefer ``fetch_campaigns`` and ``fetch_ad_performances``.
        """
        try:
            campaigns = self.fetch_campaigns(sync_mode=sync_mode, cursor=cursor)
            performances = self.fetch_ad_performances(sync_mode=sync_mode, cursor=cursor)
            if not campaigns.success:
                return campaigns
            if not performances.success:
                return performances
            data = (campaigns.data or []) + (performances.data or [])
            return ConnectorResult.ok(
                data=data,
                metadata={
                    "source_timestamp": utc_now().isoformat(),
                    "campaign_count": len(campaigns.data or []),
                    "performance_count": len(performances.data or []),
                },
            )
        except Exception as exc:
            return ConnectorResult.from_exception(exc)

    def fetch_campaigns(
        self,
        sync_mode: SyncMode = SyncMode.INCREMENTAL,
        cursor: Optional[str] = None,
        **kwargs: Any,
    ) -> ConnectorResult:
        """Fetch campaign settings from Shopee Ads.

        A synthetic ``shop-total`` campaign + ad is appended so that shop-level
        aggregate performance metrics can be linked later.
        """
        try:
            list_result = self._client.get_campaign_list(ad_type="all", offset=0, limit=100)
            if not list_result["ok"]:
                return ConnectorResult.failed(
                    message=list_result.get("error") or "Failed to fetch Shopee campaign list",
                    metadata={"status_code": list_result.get("status_code")},
                )

            campaign_list = list_result.get("response", {}).get("campaign_list", [])
            campaign_ids = [str(c.get("campaign_id")) for c in campaign_list if c.get("campaign_id")]

            campaigns: List[Dict[str, Any]] = []
            if campaign_ids:
                settings_result = self._client.get_campaign_setting_info(
                    campaign_id_list=",".join(campaign_ids[:50]),
                    info_type_list="1",
                )
                if not settings_result["ok"]:
                    return ConnectorResult.failed(
                        message=settings_result.get("error") or "Failed to fetch Shopee campaign settings",
                        metadata={"status_code": settings_result.get("status_code")},
                    )
                campaigns = settings_result.get("response", {}).get("campaign_list", [])

            # Synthetic shop-total campaign used for aggregate ad performance.
            campaigns.append({
                "campaign_id": "shop-total",
                "common_info": {
                    "ad_name": "Shop Total (Aggregate)",
                    "campaign_status": "active",
                    "ad_type": "shop_aggregate",
                    "campaign_budget": 0,
                },
                "item_list": [
                    {
                        "ad_id": "shop-total",
                        "ad_name": "Shop Total (Aggregate)",
                        "ad_status": "active",
                    }
                ],
            })

            return ConnectorResult.ok(
                data=campaigns,
                metadata={
                    "source_timestamp": utc_now().isoformat(),
                    "campaign_count": len(campaigns) - 1,  # exclude synthetic
                },
            )
        except Exception as exc:
            return ConnectorResult.from_exception(exc)

    def fetch_ad_performances(
        self,
        sync_mode: SyncMode = SyncMode.INCREMENTAL,
        cursor: Optional[str] = None,
        **kwargs: Any,
    ) -> ConnectorResult:
        """Fetch daily CPC ads performance from Shopee Ads.

        The Shopee endpoint returns shop-level aggregate rows by date. Each row is
        tagged with the synthetic ``shop-total`` campaign/ad so it can be linked to
        a canonical record.
        """
        try:
            end_date = utc_now()
            start_date = end_date - timedelta(days=7)
            start_str = start_date.strftime("%d-%m-%Y")
            end_str = end_date.strftime("%d-%m-%Y")

            perf_result = self._client.get_ads_daily_performance(start_date=start_str, end_date=end_str)
            if not perf_result["ok"]:
                return ConnectorResult.failed(
                    message=perf_result.get("error") or "Failed to fetch Shopee ads performance",
                    metadata={"status_code": perf_result.get("status_code")},
                )

            performance_data = perf_result.get("response", [])
            if not isinstance(performance_data, list):
                performance_data = []

            # Tag each row with the synthetic shop-total IDs.
            for row in performance_data:
                row["campaign_id"] = "shop-total"
                row["ad_id"] = "shop-total"

            return ConnectorResult.ok(
                data=performance_data,
                metadata={
                    "source_timestamp": utc_now().isoformat(),
                    "performance_count": len(performance_data),
                },
            )
        except Exception as exc:
            return ConnectorResult.from_exception(exc)

    def order_mapper(self) -> ShopeeOrderMapper:
        return ShopeeOrderMapper(self.tenant)

    def payment_mapper(self) -> ShopeePaymentMapper:
        return ShopeePaymentMapper(self.tenant)

    def campaign_mapper(self) -> ShopeeCampaignMapper:
        return ShopeeCampaignMapper(self.tenant)

    def ads_performance_mapper(self, provenance_repo: Any) -> ShopeeAdsPerformanceMapper:
        return ShopeeAdsPerformanceMapper(
            tenant=self.tenant,
            provenance_repo=provenance_repo,
            marketplace_code=self.marketplace_code,
            store_id=self.store_id,
        )

    def _resolve_time_range(
        self, sync_mode: SyncMode, cursor: Optional[str]
    ) -> tuple[int, int, Optional[str]]:
        now = int(time.time())
        if sync_mode == SyncMode.FULL:
            return 0, now, None

        if cursor:
            try:
                parsed = json.loads(cursor)
                time_from = int(parsed.get("time_to", now - 86400))
                page_cursor = parsed.get("page_cursor")
                return time_from, now, page_cursor
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

        return now - 7 * 86400, now, None

    def _encode_cursor(self, time_to: int, page_cursor: Optional[str]) -> str:
        return json.dumps({"time_to": time_to, "page_cursor": page_cursor})
