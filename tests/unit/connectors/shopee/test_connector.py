"""Unit tests for the Shopee marketplace connector."""

from datetime import datetime, timezone
import pytest

from commerceos.connectors.shopee import ShopeeApiClient, ShopeeConnector, ShopeeTenantContext
from commerceos.connectors.core import SyncMode
from tests.fixtures.shopee_responses import (
    order_detail_with_items_response,
    order_income_response,
    order_list_response,
    shop_info_response,
)


class FakeResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body

    def json(self):
        return self._body


@pytest.fixture
def tenant():
    return ShopeeTenantContext(
        organization_id="org-1",
        business_id="biz-1",
        store_id="store-1",
        currency="IDR",
    )


def _make_fake_request_fn(responses_by_path):
    def request_fn(method, url, params, body):
        for path, response in responses_by_path.items():
            if path in url:
                return FakeResponse(200, response["data"])
        raise RuntimeError(f"Unexpected URL: {url}")
    return request_fn


def _make_connector(tenant, responses_by_path):
    api_client = ShopeeApiClient(
        partner_id=123456,
        partner_key="fake-key",
        shop_id=123456789,
        access_token="fake-token",
        sandbox=True,
        request_fn=_make_fake_request_fn(responses_by_path),
    )
    return ShopeeConnector(
        store_id="123456789",
        tenant=tenant,
        api_client=api_client,
    )


def test_health_returns_healthy_when_authenticated(tenant):
    connector = _make_connector(tenant, {"/api/v2/shop/get_shop_info": shop_info_response()})
    # The connector's auth object checks the SecretManager, which returns
    # None for all secrets in tests, so is_authenticated is False.
    # For this test we patch the auth object to return authenticated.
    connector._auth.get_credentials = lambda: {
        "partner_id": "123456",
        "partner_key": "fake-key",
        "shop_id": "123456789",
    }
    health = connector.health()

    assert health.authenticated is True
    assert health.api_available is True
    assert health.status == "healthy"


def test_fetch_orders_returns_order_details(tenant):
    order_sn = "250101ABC123"
    connector = _make_connector(
        tenant,
        {
            "/api/v2/order/get_order_list": order_list_response([order_sn]),
            "/api/v2/order/get_order_detail": order_detail_with_items_response(order_sn),
        },
    )

    result = connector.fetch_orders(sync_mode=SyncMode.FULL)

    assert result.success is True
    assert len(result.data) == 1
    assert result.data[0]["order_sn"] == order_sn
    assert result.metadata["order_count"] == 1


def test_fetch_payments_returns_escrow_details(tenant):
    order_sn = "250101ABC123"
    connector = _make_connector(
        tenant,
        {
            "/api/v2/order/get_order_list": order_list_response([order_sn]),
            "/api/v2/payment/get_order_escrow_detail": order_income_response(order_sn),
        },
    )

    result = connector.fetch_payments(sync_mode=SyncMode.FULL)

    assert result.success is True
    assert len(result.data) == 1
    assert result.data[0]["order_sn"] == order_sn
    assert result.metadata["payment_count"] == 1


def test_fetch_orders_returns_empty_list(tenant):
    connector = _make_connector(
        tenant,
        {"/api/v2/order/get_order_list": order_list_response([])},
    )

    result = connector.fetch_orders(sync_mode=SyncMode.FULL)

    assert result.success is True
    assert result.data == []
    assert result.metadata["cursor"] is None


def test_fetch_orders_propagates_api_error(tenant):
    connector = _make_connector(
        tenant,
        {
            "/api/v2/order/get_order_list": {
                "ok": False,
                "status_code": 400,
                "data": {"error": "invalid_params", "message": "bad"},
                "error": "invalid_params",
                "response": {},
            }
        },
    )

    result = connector.fetch_orders(sync_mode=SyncMode.FULL)

    assert result.success is False
    assert result.errors[0]["message"] == "invalid_params"


def test_unauthenticated_health(tenant):
    # Constructing with store_id="" triggers the auth check to fail before
    # attempting to build an API client, so this is a safe way to exercise
    # the unauthenticated path without hitting the SecretManager.
    connector = ShopeeConnector(
        store_id="",
        tenant=tenant,
        api_client=None,
    )
    health = connector.health()

    assert health.authenticated is False
    assert health.status == "unauthenticated"
