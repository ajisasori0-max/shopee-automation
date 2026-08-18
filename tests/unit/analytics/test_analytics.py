"""Tests for Epic 5 analytics, forecasting, inventory, finance, and scenarios.
"""

import os
from datetime import timedelta

import pytest

from commerceos.analytics.engine import AdvancedAnalyticsEngine
from commerceos.analytics.finance import FinancialForecastingEngine
from commerceos.analytics.forecasting import DemandForecastingEngine
from commerceos.analytics.inventory import InventoryIntelligenceEngine
from commerceos.analytics.scenarios import ScenarioEngine
from commerceos.commerce.models import Ad, AdPerformance, Campaign, Inventory, Order, OrderItem, Payment, Product, Variant
from commerceos.platform.database.connection import create_all, get_session, reset_engine
from commerceos.shared.value_objects.primitives import utc_now


DB_URL = "sqlite:///test_analytics.db"


@pytest.fixture
def session():
    reset_engine()
    if os.path.exists("test_analytics.db"):
        os.remove("test_analytics.db")
    create_all(DB_URL)
    sess = get_session(DB_URL)
    try:
        yield sess
    finally:
        sess.close()
        reset_engine()
        if os.path.exists("test_analytics.db"):
            os.remove("test_analytics.db")


@pytest.fixture
def seeded_session(session):
    org = "org-1"
    biz = "biz-1"
    store = "store-ppm-001"
    product = Product(id="p-1", name="Widget", sku="W-001", organization_id=org, business_id=biz, store_id=store)
    variant = Variant(id="v-1", product_id="p-1", sku="W-001-RED", selling_price=100000, organization_id=org, business_id=biz, store_id=store)
    inventory = Inventory(id="inv-1", variant_id="v-1", quantity_available=10, quantity_reserved=0, organization_id=org, business_id=biz, store_id=store)
    order = Order(
        id="o-1",
        marketplace_order_id="SN-1",
        status="completed",
        payment_status="paid",
        total_amount=100000,
        ordered_at=utc_now(),
        organization_id=org,
        business_id=biz,
        store_id=store,
    )
    item = OrderItem(
        id="oi-1",
        order_id="o-1",
        product_name="Widget",
        variant_name="Red",
        sku="W-001-RED",
        quantity=100,
        unit_price=100000,
        total_price=10000000,
        organization_id=org,
        business_id=biz,
        store_id=store,
    )
    payment = Payment(
        id="pay-1",
        order_id="o-1",
        store_id=store,
        gross_amount=100000,
        fee_amount=5000,
        net_amount=95000,
        status="paid",
        paid_at=utc_now(),
        organization_id=org,
        business_id=biz,
    )
    campaign = Campaign(
        id="c-1",
        marketplace_campaign_id="MC-1",
        name="Test Campaign",
        campaign_type="shopping",
        status="active",
        budget=1000000,
        store_id=store,
        organization_id=org,
        business_id=biz,
    )
    ad = Ad(
        id="a-1",
        campaign_id="c-1",
        marketplace_ad_id="MA-1",
        name="Test Ad",
        ad_type="shopping",
        status="active",
        store_id=store,
        organization_id=org,
        business_id=biz,
    )
    ad_perf = AdPerformance(
        id="ap-1",
        ad_id="a-1",
        campaign_id="c-1",
        store_id=store,
        date=utc_now().date(),
        spend=50000,
        revenue=150000,
        clicks=100,
        impressions=1000,
        conversions=5,
        organization_id=org,
        business_id=biz,
    )
    session.add_all([product, variant, inventory, order, item, payment, campaign, ad, ad_perf])
    session.commit()
    return session


# ------------------ WP5.1 Advanced Analytics ------------------


def test_sku_profitability_reports_cogs_missing(seeded_session):
    engine = AdvancedAnalyticsEngine(seeded_session)
    result = engine.sku_profitability()
    assert result["cogs_available"] is False
    assert result["sku_count"] == 1
    assert result["skus"][0]["sku"] == "W-001-RED"
    assert any("COGS unavailable" in note for note in result["skus"][0]["notes"])


def test_campaign_profitability(seeded_session):
    engine = AdvancedAnalyticsEngine(seeded_session)
    result = engine.campaign_profitability()
    assert result["campaign_count"] == 1
    assert result["overall_roas"] > 0


def test_customer_repeat_behavior_unavailable(seeded_session):
    engine = AdvancedAnalyticsEngine(seeded_session)
    result = engine.customer_repeat_behavior()
    assert result["available"] is False
    assert "not available" in result["reason"].lower()


# ------------------ WP5.2 Demand Forecasting ------------------


def test_sales_forecast_naive(seeded_session):
    engine = DemandForecastingEngine(seeded_session)
    result = engine.sales_forecast(horizon_days=3, method="naive")
    assert result.method == "naive"
    assert len(result.points) == 3


def test_sku_demand_forecast(seeded_session):
    engine = DemandForecastingEngine(seeded_session)
    result = engine.sku_demand_forecast("W-001-RED", horizon_days=7, method="moving_average")
    assert result.metric == "sku_units:W-001-RED"
    assert len(result.points) == 7


def test_ad_spend_forecast_no_data(session):
    engine = DemandForecastingEngine(session)
    result = engine.ad_spend_forecast(horizon_days=7)
    assert result.confidence == "none"
    assert "No historical" in result.notes[0]


# ------------------ WP5.3 Inventory Intelligence ------------------


def test_inventory_recommendation(seeded_session):
    engine = InventoryIntelligenceEngine(seeded_session)
    result = engine.recommend()
    assert len(result["recommendations"]) == 1
    rec = result["recommendations"][0]
    assert rec["sku"] == "W-001-RED"
    assert rec["daily_velocity"] > 0


def test_stockout_risk(seeded_session):
    engine = InventoryIntelligenceEngine(seeded_session)
    result = engine.stockout_risk(days_ahead=14)
    assert "at_risk_count" in result


# ------------------ WP5.4 Financial Forecasting ------------------


def test_actual_pnl_reports_cogs_missing(seeded_session):
    engine = FinancialForecastingEngine(seeded_session)
    result = engine.actual_pnl()
    assert result["cogs"] is None
    assert result["revenue"] > 0
    assert any("COGS" in note for note in result["notes"])


def test_cash_forecast_reports_opening_cash_missing(seeded_session):
    engine = FinancialForecastingEngine(seeded_session)
    result = engine.cash_forecast(horizon_days=7)
    assert result["opening_cash"] is None
    assert any("Opening cash" in note for note in result["notes"])


# ------------------ WP5.5 Scenario Engine ------------------


def test_ad_spend_increase_scenario(seeded_session):
    engine = ScenarioEngine(seeded_session)
    result = engine.ad_spend_increase(increase_pct=20, horizon_days=7)
    assert result["scenario_type"] == "ad_spend_increase"
    assert "delta" in result


def test_sales_decline_scenario(seeded_session):
    engine = ScenarioEngine(seeded_session)
    result = engine.sales_decline(decline_pct=20, horizon_days=7)
    assert result["scenario_type"] == "sales_decline"
    assert result["delta"]["forecast_revenue"] < 0


def test_supplier_delay_scenario(seeded_session):
    engine = ScenarioEngine(seeded_session)
    result = engine.supplier_delay("W-001-RED", baseline_lead_time=7, scenario_lead_time=14)
    assert result["scenario_type"] == "supplier_delay"
    assert result["scenario"]["lead_time_days"] == 14


def test_unknown_scenario_type(seeded_session):
    engine = ScenarioEngine(seeded_session)
    result = engine.run("unknown_type", {})
    assert "error" in result
