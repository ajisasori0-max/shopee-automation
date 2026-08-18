"""Operational SOP Engine integration test.

Verifies that running the SOP engine through the job runner produces deterministic
results, records executions, and persists decisions without duplicates when run twice.
"""

import os

import pytest

from commerceos.commerce.models import Inventory, Order, OrderItem, Product, Variant
from commerceos.decision.models import Decision
from commerceos.jobs.factory import register_default_jobs
from commerceos.jobs.runner import JobRunner
from commerceos.platform.database.connection import create_all, get_session, reset_engine
from commerceos.shared.value_objects.primitives import utc_now
from commerceos.sop.models import SOPExecutionRecord


DB_URL = "sqlite:///test_sop_integration.db"


@pytest.fixture
def session():
    reset_engine()
    if os.path.exists("test_sop_integration.db"):
        os.remove("test_sop_integration.db")
    create_all(DB_URL)
    sess = get_session(DB_URL)
    try:
        yield sess
    finally:
        sess.close()
        reset_engine()
        if os.path.exists("test_sop_integration.db"):
            os.remove("test_sop_integration.db")


@pytest.fixture
def seeded_session(session):
    org = "org-1"
    biz = "biz-1"
    store = "store-ppm-001"
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
        selling_price=100000,
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
    session.add_all([product, variant, inventory, order, item])
    session.commit()
    return session


def test_sop_job_run_and_record_execution(seeded_session):
    registry = register_default_jobs()
    runner = JobRunner(seeded_session, registry=registry)
    result = runner.run("sop_engine_run")
    assert result["status"] == "completed"
    summary = result["result"]
    assert summary["sop_count"] == 4

    # Executions should be recorded.
    executions = seeded_session.query(SOPExecutionRecord).all()
    assert len(executions) == 4


def test_sop_job_run_is_idempotent_for_decisions(seeded_session):
    registry = register_default_jobs()
    runner = JobRunner(seeded_session, registry=registry)
    first = runner.run("sop_engine_run")
    decision_count_after_first = seeded_session.query(Decision).count()

    second = runner.run("sop_engine_run")
    decision_count_after_second = seeded_session.query(Decision).count()

    # No new decisions should be created on the second run because the same SOP titles are already open.
    assert decision_count_after_first == decision_count_after_second
    assert first["status"] == "completed"
    assert second["status"] == "completed"
