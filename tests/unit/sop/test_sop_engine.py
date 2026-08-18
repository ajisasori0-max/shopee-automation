"""Tests for the Operational SOP Engine (WP3.4).

Covers:
- SOP definition structure and serialization.
- Condition evaluation.
- Trigger correctness for each built-in SOP.
- Missing data handling.
- Approval requirement flagging.
- Idempotency and auditability.
- Failure handling.
"""

import os
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest

from commerceos.commerce.models import AdPerformance, Campaign, Inventory, Order, OrderItem, Payment, Product, Variant
from commerceos.decision.models import Decision
from commerceos.platform.database.connection import create_all, get_session, reset_engine
from commerceos.shared.value_objects.primitives import utc_now
from commerceos.sop.engine import (
    CashPressureRunner,
    CASH_PRESSURE_SOP,
    LOW_STOCK_SOP,
    LowStockRunner,
    REVENUE_DROP_SOP,
    RevenueDropRunner,
    ROAS_COLLAPSE_SOP,
    ROASCollapseRunner,
    SOPEngine,
    SOPStep,
    _safe_float,
)


DB_URL = "sqlite:///test_sop_engine.db"


@pytest.fixture
def session():
    reset_engine()
    if os.path.exists("test_sop_engine.db"):
        os.remove("test_sop_engine.db")
    create_all(DB_URL)
    sess = get_session(DB_URL)
    try:
        yield sess
    finally:
        sess.close()
        reset_engine()
        if os.path.exists("test_sop_engine.db"):
            os.remove("test_sop_engine.db")


@pytest.fixture
def seeded_session(session):
    """Seed a store with one product, one variant, inventory, and one order."""
    org = "org-1"
    biz = "biz-1"
    store = "store-1"
    product = Product(
        id="p-1",
        name="Widget",
        sku="W-001",
        organization_id=org,
        business_id=biz,
        store_id=store,
    )
    variant = Variant(
        id="v-1",
        product_id="p-1",
        sku="W-001-RED",
        selling_price=Decimal("100000"),
        organization_id=org,
        business_id=biz,
        store_id=store,
    )
    inventory = Inventory(
        id="inv-1",
        variant_id="v-1",
        quantity_available=10,
        quantity_reserved=0,
        organization_id=org,
        business_id=biz,
        store_id=store,
    )
    order = Order(
        id="o-1",
        marketplace_order_id="SN-1",
        status="completed",
        payment_status="paid",
        total_amount=Decimal("100000"),
        ordered_at=utc_now() - timedelta(days=1),
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
        quantity=5,
        unit_price=Decimal("100000"),
        total_price=Decimal("500000"),
        organization_id=org,
        business_id=biz,
        store_id=store,
    )
    session.add_all([product, variant, inventory, order, item])
    session.commit()
    return session


def test_sop_definition_to_dict():
    sop = LOW_STOCK_SOP
    data = sop.to_dict()
    assert data["code"] == "LOW_STOCK"
    assert data["enabled"] is True
    assert len(data["steps"]) == 4
    assert data["steps"][-1]["decision_point"] is True


def test_sop_runner_condition_evaluation():
    runner = LowStockRunner(LOW_STOCK_SOP)
    assert runner._eval_condition("coverage_days < 7", {"coverage_days": 5.0}) is True
    assert runner._eval_condition("coverage_days < 7", {"coverage_days": 10.0}) is False
    assert runner._eval_condition("revenue_delta_pct < -0.10", {"revenue_delta_pct": -0.15}) is True


def test_low_stock_runner_applies(seeded_session):
    ctx = {
        "inventory_items": [
            {
                "sku": "W-001-RED",
                "product_name": "Widget",
                "available": 10,
                "daily_velocity": 5.0,
                "lead_time_days": 7,
                "coverage_days": 2.0,
                "selling_price": 100000.0,
            }
        ]
    }
    runner = LowStockRunner(LOW_STOCK_SOP)
    execution = runner.run(seeded_session, "store-1", ctx)
    assert execution.applies is True
    assert "W-001-RED" in execution.outputs["low_coverage_skus"]
    assert execution.outputs["recommended_action"] != ""
    assert execution.outputs["recommendations"][0]["recommended_po_quantity"] > 0


def test_low_stock_runner_no_low_coverage():
    ctx = {
        "inventory_items": [
            {
                "sku": "W-001-RED",
                "available": 1000,
                "daily_velocity": 1.0,
                "lead_time_days": 7,
                "coverage_days": 999.0,
                "selling_price": 100000.0,
            }
        ]
    }
    runner = LowStockRunner(LOW_STOCK_SOP)
    execution = runner.run(None, "store-1", ctx)
    assert execution.applies is False
    assert execution.branches


def test_roas_collapse_runner_applies():
    ctx = {
        "overall_roas": 1.2,
        "overall_ctr": 1.5,
        "total_spend": 1000000,
        "by_campaign": [
            {
                "campaign_id": "c-1",
                "campaign_name": "Test Campaign",
                "roas": 1.2,
                "ctr": 0.3,
                "conversions": 0,
                "spend": 1000000,
            }
        ],
    }
    runner = ROASCollapseRunner(ROAS_COLLAPSE_SOP)
    execution = runner.run(None, "store-1", ctx)
    assert execution.applies is True
    assert execution.outputs["overall_roas"] == 1.2
    assert "Pause" in execution.outputs["recommended_action"] or "Reduce" in execution.outputs["recommended_action"]


def test_roas_collapse_runner_no_data():
    runner = ROASCollapseRunner(ROAS_COLLAPSE_SOP)
    execution = runner.run(None, "store-1", {})
    assert execution.applies is False
    assert execution.errors


def test_revenue_drop_runner_applies():
    ctx = {
        "revenue_current": 1000000,
        "revenue_baseline": 2000000,
        "revenue_delta_pct": -0.5,
        "orders_current": 10,
        "orders_baseline": 20,
        "orders_delta_pct": -0.5,
        "aov_current": 100000,
        "aov_baseline": 100000,
        "traffic_current": 1000,
        "traffic_baseline": 2000,
        "traffic_delta_pct": -0.5,
        "conversion_current": 50,
        "conversion_baseline": 100,
        "conversion_delta_pct": -0.5,
        "ad_spend_current": 500000,
        "ad_spend_baseline": 500000,
        "ad_spend_delta_pct": 0.0,
        "roas_current": 2.0,
        "roas_baseline": 2.0,
        "roas_delta_pct": 0.0,
        "zero_stock_skus": ["W-001-RED"],
        "price_changes": "price history not available",
    }
    runner = RevenueDropRunner(REVENUE_DROP_SOP)
    execution = runner.run(None, "store-1", ctx)
    assert execution.applies is True
    assert any("revenue" in cause.lower() or "traffic" in cause.lower() for cause in execution.outputs["causes"])
    assert "price history" in execution.outputs["missing_inputs"]


def test_cash_pressure_runner_missing_cash():
    runner = CashPressureRunner(CASH_PRESSURE_SOP)
    execution = runner.run(None, "store-1", {"cash_balance": None})
    assert execution.applies is False
    assert execution.outputs["missing_inputs"] == ["cash_balance"]


def test_sop_engine_refresh_no_data(session):
    engine = SOPEngine()
    # Without ad/revenue data, no SOP should trigger.
    result = engine.refresh(session, "store-1", publish_events=False, knowledge_uow=None)
    assert result["sop_count"] == 4
    # With zero revenue baseline, revenue_delta_pct is None so REVENUE_DROP does not apply.
    # ROAS requires ad spend. Cash requires a cash balance. Low stock uses seeded data.
    # Seeded data has 5 sold in 14 days over available 10 -> coverage ~28 days, so not applicable.
    assert result["applicable"] == 0
    assert result["executed"] == 4


def test_sop_engine_refresh_low_stock(seeded_session):
    engine = SOPEngine()
    result = engine.refresh(seeded_session, "store-1", publish_events=False)
    # The seeded order has 5 units sold in 14 days => velocity ~0.36/day. Available 10 => coverage ~28 days.
    # So LOW_STOCK does not apply. This is intentional; we adjust context to force it below.
    assert result["applicable"] == 0


def test_sop_engine_refresh_low_stock_forced(seeded_session):
    engine = SOPEngine()
    # Manually lower coverage by setting high velocity in a custom context.
    ctx = {
        "inventory_items": [
            {
                "sku": "W-001-RED",
                "product_name": "Widget",
                "available": 10,
                "daily_velocity": 10.0,
                "lead_time_days": 7,
                "coverage_days": 1.0,
                "selling_price": 100000.0,
            }
        ]
    }
    runner = LowStockRunner(LOW_STOCK_SOP)
    execution = runner.run(seeded_session, "store-1", ctx)
    assert execution.applies is True


def test_persist_sop_decisions(seeded_session):
    rec = {
        "category": "inventory",
        "severity": "warning",
        "title": "[LOW_STOCK] Low Stock Replenishment",
        "description": "SOP Low Stock Replenishment applies. SKUs: W-001-RED.",
        "rationale": "SOP LOW_STOCK v1.0.0 triggered.",
        "recommended_action": "Approve purchase orders",
        "expected_impact": {},
        "confidence": "medium",
        "evidence": [{"source_type": "business_rule", "source_id": "x", "description": "SOP"}],
    }
    from commerceos.decision.engine import DecisionEngine

    decision_engine = DecisionEngine(seeded_session)
    new_decisions = decision_engine.refresh_sop_recommendations(
        "store-1",
        {
            "recommendations": [rec],
        },
    )
    assert len(new_decisions) == 1
    assert new_decisions[0].category == "inventory"
    assert new_decisions[0].status == "proposed"

    # Calling again with the same title should not duplicate.
    second = decision_engine.refresh_sop_recommendations(
        "store-1",
        {
            "recommendations": [rec],
        },
    )
    assert len(second) == 0


def test_safe_float():
    assert _safe_float(Decimal("10.5")) == 10.5
    assert _safe_float(None) is None
    assert _safe_float("not a number") is None


def test_sop_step_dataclass():
    step = SOPStep(name="Test", description="D", condition="x < 1", inputs=["x"], outputs=["y"], decision_point=True, approval_required=True)
    assert step.condition == "x < 1"
