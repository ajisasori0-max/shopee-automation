"""Integration test: Shopee connector wired through the SyncEngine."""

import uuid
from datetime import datetime, timezone

import pytest

from commerceos.commerce.models import Order, OrderItem, Payment
from commerceos.connectors.core import SyncMode
from commerceos.connectors.shopee import ShopeeApiClient, ShopeeConnector, ShopeeOrderMapper, ShopeePaymentMapper, ShopeeTenantContext
from commerceos.ingestion import SyncEngine, sqlalchemy_ingestion_uow
from commerceos.ingestion.models import SyncRun, SyncProvenance, RawPayload
from commerceos.platform.database.connection import create_all, get_session, reset_engine
from tests.fixtures.shopee_responses import (
    order_detail_with_items_response,
    order_income_response,
    order_list_response,
    shop_info_response,
)


DATABASE_URL = "sqlite:///:memory:"


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


@pytest.fixture
def session():
    reset_engine()
    create_all(DATABASE_URL)
    sess = get_session(DATABASE_URL)
    try:
        yield sess
    finally:
        sess.close()
        reset_engine()


def _build_api_client(responses_by_path):
    def request_fn(method, url, params, body):
        for path, response in responses_by_path.items():
            if path in url:
                return FakeResponse(200, response["data"])
        raise RuntimeError(f"Unexpected URL: {url}")

    return ShopeeApiClient(
        partner_id=123456,
        partner_key="fake-key",
        shop_id=123456789,
        access_token="fake-token",
        sandbox=True,
        request_fn=request_fn,
    )


def _build_connector(tenant, responses_by_path):
    return ShopeeConnector(
        store_id="123456789",
        tenant=tenant,
        api_client=_build_api_client(responses_by_path),
    )


def test_sync_engine_persists_shopee_order_and_items(session, tenant):
    order_sn = "250101ABC123"
    connector = _build_connector(
        tenant,
        {
            "/api/v2/order/get_order_list": order_list_response([order_sn]),
            "/api/v2/order/get_order_detail": order_detail_with_items_response(order_sn),
        },
    )

    with sqlalchemy_ingestion_uow(session) as uow:
        engine = SyncEngine(uow=uow)
        engine.register_mapper("orders", ShopeeOrderMapper(tenant))
        result = engine.sync(connector, entity_type="orders", store_id="123456789")

    assert result.success is True
    assert result.metadata["records_received"] == 1
    assert result.metadata["records_persisted"] == 1  # 1 raw payload

    with session:
        orders = session.query(Order).all()
        items = session.query(OrderItem).all()
        raw = session.query(RawPayload).all()
        provenance = session.query(SyncProvenance).all()
        sync_runs = session.query(SyncRun).all()

        assert len(orders) == 1
        assert orders[0].marketplace_order_id == order_sn
        assert orders[0].status == "COMPLETED"

        assert len(items) == 1
        assert items[0].order_id == orders[0].id
        assert items[0].quantity == 2

        assert len(raw) == 1
        assert raw[0].external_entity_id == order_sn

        assert len(provenance) == 2
        assert len(sync_runs) == 1
        assert sync_runs[0].status == "completed"


def test_sync_engine_persists_shopee_payment(session, tenant):
    order_sn = "250101ABC123"
    connector = _build_connector(
        tenant,
        {
            "/api/v2/order/get_order_list": order_list_response([order_sn]),
            "/api/v2/payment/get_order_escrow_detail": order_income_response(order_sn),
        },
    )

    with sqlalchemy_ingestion_uow(session) as uow:
        engine = SyncEngine(uow=uow)
        engine.register_mapper("payments", ShopeePaymentMapper(tenant))
        result = engine.sync(connector, entity_type="payments", store_id="123456789")

    assert result.success is True
    assert result.metadata["records_persisted"] == 1

    with session:
        # The order does not exist in this sync run, so payment cannot be linked.
        # But it should still be persisted as a standalone record.
        payments = session.query(Payment).all()
        assert len(payments) == 1
        assert payments[0].marketplace_payment_id == "QRIS"
        assert payments[0].order_id is None


def test_sync_engine_order_then_payment_links_them(session, tenant):
    order_sn = "250101ABC123"
    connector = _build_connector(
        tenant,
        {
            "/api/v2/order/get_order_list": order_list_response([order_sn]),
            "/api/v2/order/get_order_detail": order_detail_with_items_response(order_sn),
            "/api/v2/payment/get_order_escrow_detail": order_income_response(order_sn),
        },
    )

    with sqlalchemy_ingestion_uow(session) as uow:
        engine = SyncEngine(uow=uow)
        engine.register_mapper("orders", ShopeeOrderMapper(tenant))
        engine.register_mapper("payments", ShopeePaymentMapper(tenant))
        engine.sync(connector, entity_type="orders", store_id="123456789")
        result = engine.sync(connector, entity_type="payments", store_id="123456789")

    assert result.success is True

    with session:
        orders = session.query(Order).all()
        payments = session.query(Payment).all()
        assert len(orders) == 1
        assert len(payments) == 1
        assert payments[0].order_id == orders[0].id
