"""Unit tests for Shopee mappers."""

import pytest
from decimal import Decimal
from datetime import datetime, timezone

from commerceos.commerce.models import Order, OrderItem, Payment
from commerceos.connectors.shopee.mappers import ShopeeOrderMapper, ShopeePaymentMapper, ShopeeTenantContext
from tests.fixtures.shopee_responses import order_detail_with_items_response, order_income_response, sample_item


@pytest.fixture
def tenant():
    return ShopeeTenantContext(
        organization_id="org-1",
        business_id="biz-1",
        store_id="store-1",
        currency="IDR",
    )


def test_order_mapper_creates_order_and_items(tenant):
    mapper = ShopeeOrderMapper(tenant)
    raw = order_detail_with_items_response("250101ABC123")["response"]["order_list"][0]

    entities = mapper.map(raw)

    order_entities = [e for e in entities if e.entity_type == "order"]
    item_entities = [e for e in entities if e.entity_type == "order_item"]

    assert len(order_entities) == 1
    assert len(item_entities) == 1

    order = order_entities[0]
    assert order.model_class == Order
    assert order.data["marketplace_order_id"] == "250101ABC123"
    assert order.data["status"] == "COMPLETED"
    assert order.data["currency"] == "IDR"
    assert order.data["subtotal"] == Decimal("250000")
    assert order.data["shipping_cost"] == Decimal("15000")
    assert order.data["discount"] == Decimal("15000")
    assert order.data["total_amount"] == Decimal("250000")
    assert order.data["organization_id"] == "org-1"
    assert order.data["ordered_at"] == datetime.fromtimestamp(1700000000, tz=timezone.utc)
    assert order.data["paid_at"] == datetime.fromtimestamp(1700000100, tz=timezone.utc)

    item = item_entities[0]
    assert item.model_class == OrderItem
    assert item.data["product_name"] == "Test Product"
    assert item.data["quantity"] == 2
    assert item.data["unit_price"] == Decimal("125000")
    assert item.data["total_price"] == Decimal("250000")
    assert item.parent_external_id == "250101ABC123"
    assert item.parent_field == "order_id"


def test_payment_mapper_creates_payment(tenant):
    mapper = ShopeePaymentMapper(tenant)
    raw = order_income_response("250101ABC123")["response"]["order_income_list"][0]

    entities = mapper.map(raw)

    assert len(entities) == 1
    payment = entities[0]
    assert payment.model_class == Payment
    assert payment.data["payment_type"] == "order"
    assert payment.data["status"] == "RELEASED"
    assert payment.data["gross_amount"] == Decimal("255000")
    assert payment.data["fee_amount"] == Decimal("15300")
    assert payment.data["net_amount"] == Decimal("239700")
    assert payment.data["paid_at"] == datetime.fromtimestamp(1700001000, tz=timezone.utc)
    assert payment.data["organization_id"] == "org-1"


def test_order_mapper_requires_order_sn(tenant):
    mapper = ShopeeOrderMapper(tenant)
    with pytest.raises(ValueError, match="order_sn"):
        mapper.map({})


def test_payment_mapper_requires_order_sn(tenant):
    mapper = ShopeePaymentMapper(tenant)
    with pytest.raises(ValueError, match="order_sn"):
        mapper.map({})
