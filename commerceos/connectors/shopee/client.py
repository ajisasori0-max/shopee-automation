"""Shopee API client for the new ingestion connector.

This client is intentionally thin and transport-agnostic. By default it uses
``requests``, but tests can inject a fake ``request_fn`` to simulate Shopee
responses without network access.

It only handles the shop-level Open API v2 endpoints needed for ingestion:
- orders list + detail
- order escrow / income (used for payments)

Signature generation follows Shopee's documented HMAC-SHA256 scheme.
"""
from __future__ import annotations


import hashlib
import hmac
import json
import time
from typing import Any, Callable, Dict, Optional

import requests


def generate_shopee_sign(
    partner_id: int,
    partner_key: str,
    path: str,
    timestamp: int,
    access_token: Optional[str] = None,
    shop_id: Optional[int] = None,
) -> str:
    """Generate a Shopee Open API v2 HMAC-SHA256 signature.

    Public API base string: ``partner_id + path + timestamp``
    Shop API base string: ``partner_id + path + timestamp + access_token + shop_id``
    """
    base = f"{partner_id}{path}{timestamp}"
    if access_token is not None and shop_id is not None:
        base += f"{access_token}{shop_id}"
    return hmac.new(
        partner_key.encode("utf-8"),
        base.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


class ShopeeApiClient:
    """Low-level Shopee API client with injectable transport."""

    def __init__(
        self,
        partner_id: int,
        partner_key: str,
        shop_id: int,
        access_token: Optional[str] = None,
        sandbox: bool = False,
        base_url: Optional[str] = None,
        request_fn: Optional[Callable[[str, str, Dict[str, Any], Dict[str, Any]], Any]] = None,
    ):
        self.partner_id = partner_id
        self.partner_key = partner_key
        self.shop_id = shop_id
        self.access_token = access_token
        self.sandbox = sandbox
        self.base_url = base_url or (
            "https://openplatform.sandbox.test-stable.shopee.sg"
            if sandbox
            else "https://partner.shopeemobile.com"
        )
        self.request_fn = request_fn or _requests_request

    def _build_query_params(
        self,
        path: str,
        timestamp: Optional[int] = None,
        include_auth: bool = True,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        ts = timestamp or int(time.time())
        params: Dict[str, Any] = {
            "partner_id": self.partner_id,
            "timestamp": ts,
            "sign": generate_shopee_sign(
                partner_id=self.partner_id,
                partner_key=self.partner_key,
                path=path,
                timestamp=ts,
                access_token=self.access_token if include_auth else None,
                shop_id=self.shop_id if include_auth else None,
            ),
        }
        if include_auth:
            params["access_token"] = self.access_token
            params["shop_id"] = self.shop_id
        if extra:
            params.update(extra)
        return params

    def _call(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        include_auth: bool = True,
    ) -> Dict[str, Any]:
        query_params = self._build_query_params(path, extra=params, include_auth=include_auth)
        url = f"{self.base_url}{path}"
        response = self.request_fn(method, url, query_params, body or {})
        return _parse_response(response)

    def get_shop_info(self) -> Dict[str, Any]:
        return self._call("GET", "/api/v2/shop/get_shop_info")

    def get_order_list(
        self,
        time_from: int,
        time_to: int,
        time_range_field: str = "update_time",
        page_size: int = 100,
        cursor: Optional[str] = None,
        order_status: str = "ALL",
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "time_from": time_from,
            "time_to": time_to,
            "time_range_field": time_range_field,
            "page_size": page_size,
        }
        if cursor:
            params["cursor"] = cursor
        if order_status != "ALL":
            params["order_status"] = order_status
        return self._call("GET", "/api/v2/order/get_order_list", params=params)

    def get_order_detail(self, order_sn_list: str) -> Dict[str, Any]:
        return self._call(
            "GET",
            "/api/v2/order/get_order_detail",
            params={
                "order_sn_list": order_sn_list,
                "response_optional_fields": (
                    "item_list,total_amount,buyer_user_id,buyer_username,"
                    "estimated_shipping_fee,recipient_address,actual_shipping_fee,"
                    "pay_time,payment_method"
                ),
            },
        )

    def get_order_income(self, order_sn_list: str) -> Dict[str, Any]:
        return self._call(
            "GET",
            "/api/v2/payment/get_order_escrow_detail",
            params={"order_sn_list": order_sn_list},
        )

    def get_campaign_list(
        self,
        ad_type: str = "all",
        offset: int = 0,
        limit: int = 100,
    ) -> Dict[str, Any]:
        return self._call(
            "GET",
            "/api/v2/ads/get_product_level_campaign_id_list",
            params={"ad_type": ad_type, "offset": offset, "limit": limit},
        )

    def get_campaign_setting_info(
        self,
        campaign_id_list: str,
        info_type_list: str = "1",
    ) -> Dict[str, Any]:
        return self._call(
            "GET",
            "/api/v2/ads/get_product_level_campaign_setting_info",
            params={
                "campaign_id_list": campaign_id_list,
                "info_type_list": info_type_list,
            },
        )

    def get_ads_daily_performance(
        self,
        start_date: str,
        end_date: str,
    ) -> Dict[str, Any]:
        """Get daily CPC ads performance.

        Dates must be in ``DD-MM-YYYY`` format.
        """
        return self._call(
            "GET",
            "/api/v2/ads/get_all_cpc_ads_daily_performance",
            params={"start_date": start_date, "end_date": end_date},
        )


def _requests_request(
    method: str, url: str, params: Dict[str, Any], body: Dict[str, Any]
) -> requests.Response:
    """Default transport using ``requests``."""
    headers = {"Content-Type": "application/json"}
    if method.upper() == "GET":
        return requests.get(url, params=params, headers=headers, timeout=30)
    return requests.post(url, params=params, json=body, headers=headers, timeout=30)


def _parse_response(response: Any) -> Dict[str, Any]:
    """Normalize a Shopee response into a dict usable by the connector.

    The ``response`` may be a real ``requests.Response`` or a test fake that has
    ``status_code`` and ``json()`` attributes.
    """
    status_code = getattr(response, "status_code", 200)
    try:
        data = response.json()
    except Exception:
        try:
            data = json.loads(response.text)
        except Exception:
            data = {}

    error = data.get("error", "") if isinstance(data, dict) else ""
    shopee_response = data.get("response", {}) if isinstance(data, dict) else {}

    return {
        "ok": status_code == 200 and not error,
        "status_code": status_code,
        "data": data,
        "error": error,
        "response": shopee_response,
    }
