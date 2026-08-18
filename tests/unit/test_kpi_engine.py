"""Tests for the KPI Engine."""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from commerceos.commerce.models import (
    Ad,
    AdPerformance,
    Business,
    Campaign,
    Marketplace,
    Order,
    Organization,
    Payment,
    Product,
    Store,
    Variant,
)
from commerceos.kpi.engine import KPIEngine
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
def engine(session):
    return KPIEngine(session)


def _seed_store(session):
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


def test_refresh_creates_kpis_and_commerce_state(session, engine):
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

    result = engine.refresh("store-1", "org-1", "biz-1", start=now - timedelta(days=1), end=now + timedelta(days=1))

    assert result["store_id"] == "store-1"
    assert result["kpi_count"] > 0
    assert result["commerce_state_id"]

    from commerceos.commerce.models import KPI, CommerceState

    kpis = session.query(KPI).filter_by(store_id="store-1").all()
    codes = {k.code for k in kpis}
    assert "gross_sales" in codes
    assert "net_sales" in codes
    assert "shopee_fees" in codes
    assert "gross_profit" in codes
    assert "aov" in codes

    state = session.query(CommerceState).filter_by(store_id="store-1").first()
    assert state is not None
    assert state.summary["gross_sales"] == 105000.0


def test_refresh_ads_kpis(session, engine):
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

    engine.refresh("store-1", "org-1", "biz-1", start=now - timedelta(days=1), end=now + timedelta(days=1))

    from commerceos.commerce.models import KPI

    kpis = {k.code: k for k in session.query(KPI).filter_by(store_id="store-1").all()}
    assert kpis["ad_spend"].value == Decimal("150000")
    assert kpis["ad_revenue"].value == Decimal("450000")
    assert kpis["roas"].value == Decimal("3.00")
    assert kpis["ctr"].value == Decimal("2.50")


def test_aggregate_kpis_averages(session):
    from commerceos.commerce.models import KPI

    k1 = KPI(code="roas", value=Decimal("2.0"), name="ROAS", unit="x", freshness=datetime.now(timezone.utc))
    k2 = KPI(code="roas", value=Decimal("4.0"), name="ROAS", unit="x", freshness=datetime.now(timezone.utc) - timedelta(days=1))
    result = KPIEngine.aggregate_kpis([k1, k2], ["roas"], average_codes=["roas"])
    assert result["roas"] == Decimal("3.00")


def test_aggregate_kpis_sums(session):
    from commerceos.commerce.models import KPI

    k1 = KPI(code="ad_spend", value=Decimal("100000"), name="Ad Spend", unit="IDR", freshness=datetime.now(timezone.utc))
    k2 = KPI(code="ad_spend", value=Decimal("50000"), name="Ad Spend", unit="IDR", freshness=datetime.now(timezone.utc) - timedelta(days=1))
    result = KPIEngine.aggregate_kpis([k1, k2], ["ad_spend"])
    assert result["ad_spend"] == Decimal("150000.00")
