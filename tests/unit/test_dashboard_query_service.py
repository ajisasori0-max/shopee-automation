"""Unit tests for the Dashboard Query Service."""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from commerceos.commerce.models import Ad, AdPerformance, Campaign, Order, Payment
from commerceos.dashboard.query_service import DashboardQueryService
from commerceos.ingestion.models import SyncCheckpoint, SyncRun
from commerceos.platform.database.connection import create_all, get_session, reset_engine


DATABASE_URL = "sqlite:///:memory:"


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


@pytest.fixture
def qs(session):
    return DashboardQueryService(session=session)


def _seed_store(session):
    from commerceos.commerce.models import Business, Marketplace, Organization, Store
    from commerceos.platform.database.models import new_uuid

    org = Organization(id="org-1", name="Test Org", slug="test")
    session.add(org)
    session.flush()

    biz = Business(id="biz-1", organization_id="org-1", name="Test Biz")
    session.add(biz)
    session.flush()

    mkt = Marketplace(id="mkt-1", code="shopee", name="Shopee")
    session.add(mkt)
    session.flush()

    store = Store(
        id="store-1",
        business_id="biz-1",
        marketplace_id="mkt-1",
        marketplace_store_id="123",
        name="Test Store",
        organization_id="org-1",
        store_id="store-1",
    )
    session.add(store)
    session.flush()
    return store


def test_get_sync_health_empty(qs):
    result = qs.get_sync_health("store-1")
    assert result == []


def test_get_freshness_empty(qs):
    result = qs.get_freshness("store-1")
    assert result == {}


def test_get_pl_summary_empty(qs):
    result = qs.get_pl_summary("store-1", datetime.now(timezone.utc) - timedelta(days=30), datetime.now(timezone.utc))
    assert result["order_count"] == 0
    assert result["gross_sales"] == 0.0
    assert result["temporary"] is True


def test_get_ad_performance_summary_empty(qs):
    result = qs.get_ad_performance_summary("store-1", datetime.now(timezone.utc) - timedelta(days=30), datetime.now(timezone.utc))
    assert result["total_spend"] == 0.0
    assert result["roas"] == 0.0


def test_get_daily_sales_with_data(qs, session):
    store = _seed_store(session)
    now = datetime.now(timezone.utc)

    order = Order(
        marketplace_order_id="order-1",
        status="COMPLETED",
        payment_status="paid",
        currency="IDR",
        subtotal=100000,
        shipping_cost=10000,
        discount=5000,
        tax=0,
        total_amount=105000,
        platform_fee=0,
        commission=0,
        shipping_subsidy=0,
        ordered_at=now,
        organization_id="org-1",
        business_id="biz-1",
        store_id="store-1",
    )
    session.add(order)
    session.flush()

    payment = Payment(
        order_id=order.id,
        marketplace_payment_id="pay-1",
        payment_type="order",
        status="RELEASED",
        currency="IDR",
        gross_amount=105000,
        fee_amount=5250,
        net_amount=99750,
        paid_at=now,
        organization_id="org-1",
        business_id="biz-1",
        store_id="store-1",
    )
    session.add(payment)
    session.commit()

    result = qs.get_daily_sales("store-1", now - timedelta(days=1), now + timedelta(days=1))

    assert len(result) == 1
    assert result[0]["order_count"] == 1
    assert result[0]["gross_sales"] == 105000.0
    assert result[0]["net_income"] == 99750.0


def test_get_pl_summary_with_data(qs, session):
    store = _seed_store(session)
    now = datetime.now(timezone.utc)

    order = Order(
        marketplace_order_id="order-1",
        status="COMPLETED",
        payment_status="paid",
        currency="IDR",
        subtotal=100000,
        shipping_cost=10000,
        discount=5000,
        tax=0,
        total_amount=105000,
        platform_fee=0,
        commission=0,
        shipping_subsidy=0,
        ordered_at=now,
        organization_id="org-1",
        business_id="biz-1",
        store_id="store-1",
    )
    session.add(order)
    session.flush()

    payment = Payment(
        order_id=order.id,
        marketplace_payment_id="pay-1",
        payment_type="order",
        status="RELEASED",
        currency="IDR",
        gross_amount=105000,
        fee_amount=5250,
        net_amount=99750,
        paid_at=now,
        organization_id="org-1",
        business_id="biz-1",
        store_id="store-1",
    )
    session.add(payment)
    session.commit()

    result = qs.get_pl_summary("store-1", now - timedelta(days=1), now + timedelta(days=1))

    assert result["order_count"] == 1
    assert result["gross_sales"] == 105000.0
    assert result["discounts"] == 5000.0
    assert result["net_sales"] == 100000.0
    assert result["shopee_fees"] == 5250.0
    assert result["gross_profit"] == 94750.0
    assert result["aov"] == 105000.0


def test_get_ad_performance_summary_with_data(qs, session):
    store = _seed_store(session)
    now = datetime.now(timezone.utc)

    campaign = Campaign(
        marketplace_campaign_id="camp-1",
        name="Test Campaign",
        campaign_type="manual",
        status="ONGOING",
        organization_id="org-1",
        business_id="biz-1",
        store_id="store-1",
    )
    session.add(campaign)
    session.flush()

    ad = Ad(
        campaign_id=campaign.id,
        marketplace_ad_id="ad-1",
        name="Test Ad",
        ad_type="manual",
        status="ONGOING",
        organization_id="org-1",
        business_id="biz-1",
        store_id="store-1",
    )
    session.add(ad)
    session.flush()

    perf = AdPerformance(
        ad_id=ad.id,
        campaign_id=campaign.id,
        date=now,
        impressions=10000,
        clicks=250,
        conversions=10,
        spend=150000,
        revenue=450000,
        roas=3.0,
        organization_id="org-1",
        business_id="biz-1",
        store_id="store-1",
    )
    session.add(perf)
    session.commit()

    result = qs.get_ad_performance_summary("store-1", now - timedelta(days=1), now + timedelta(days=1))

    assert result["total_spend"] == 150000.0
    assert result["total_revenue"] == 450000.0
    assert result["total_impressions"] == 10000
    assert result["total_clicks"] == 250
    assert result["total_conversions"] == 10
    assert result["roas"] == 3.0
    assert result["ctr"] == 2.5


def test_get_order_list_with_data(qs, session):
    store = _seed_store(session)
    now = datetime.now(timezone.utc)

    order = Order(
        marketplace_order_id="order-1",
        status="COMPLETED",
        payment_status="paid",
        currency="IDR",
        subtotal=100000,
        shipping_cost=10000,
        discount=5000,
        tax=0,
        total_amount=105000,
        platform_fee=0,
        commission=0,
        shipping_subsidy=0,
        ordered_at=now,
        organization_id="org-1",
        business_id="biz-1",
        store_id="store-1",
    )
    session.add(order)
    session.commit()

    result = qs.get_order_list("store-1", now - timedelta(days=1), now + timedelta(days=1))

    assert len(result) == 1
    assert result[0]["order_sn"] == "order-1"
    assert result[0]["total_amount"] == 105000.0


def test_get_commerce_state(qs, session):
    store = _seed_store(session)
    now = datetime.now(timezone.utc)

    run = SyncRun(
        connector_code="shopee",
        store_id="store-1",
        entity_type="orders",
        sync_mode="full",
        connector_version="1.0.0",
        status="completed",
        completed_at=now,
    )
    session.add(run)
    session.commit()

    result = qs.get_commerce_state("store-1")

    assert result["store_id"] == "store-1"
    assert result["temporary"] is True
    assert "last_sync" in result
