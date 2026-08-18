"""Unit tests for ingestion audit utilities."""

import pytest
from datetime import datetime, timezone

from commerceos.commerce.models import Order, Payment
from commerceos.ingestion import (
    find_missing_provenance,
    payload_diff,
    provenance_report,
    raw_payload_summary,
    sync_run_report,
)
from commerceos.ingestion.models import RawPayload, SyncProvenance, SyncRun
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


def _make_sync_run(session, **kwargs):
    run = SyncRun(
        connector_code=kwargs.get("connector_code", "shopee"),
        store_id=kwargs.get("store_id", "store-1"),
        entity_type=kwargs.get("entity_type", "orders"),
        sync_mode=kwargs.get("sync_mode", "full"),
        connector_version=kwargs.get("connector_version", "1.0.0"),
        status=kwargs.get("status", "completed"),
    )
    session.add(run)
    session.flush()
    return run


def _make_raw_payload(session, sync_run_id, **kwargs):
    payload = RawPayload(
        sync_run_id=sync_run_id,
        marketplace_code=kwargs.get("marketplace_code", "shopee"),
        store_id=kwargs.get("store_id", "store-1"),
        entity_type=kwargs.get("entity_type", "orders"),
        external_entity_id=kwargs.get("external_entity_id", "order-1"),
        payload_hash=kwargs.get("payload_hash", "hash-1"),
        payload=kwargs.get("payload", {"id": "order-1"}),
        connector_version=kwargs.get("connector_version", "1.0.0"),
    )
    session.add(payload)
    session.flush()
    return payload


def test_raw_payload_summary(session):
    run = _make_sync_run(session)
    _make_raw_payload(session, run.id)

    result = raw_payload_summary(session)

    assert len(result) == 1
    assert result[0]["external_entity_id"] == "order-1"
    assert result[0]["marketplace_code"] == "shopee"


def test_provenance_report(session):
    run = _make_sync_run(session)
    payload = _make_raw_payload(session, run.id)
    provenance = SyncProvenance(
        canonical_entity_type="order",
        canonical_entity_id="order-uuid-1",
        raw_payload_id=payload.id,
        marketplace_code="shopee",
        store_id="store-1",
        external_entity_id="order-1",
        sync_run_id=run.id,
        connector_version="1.0.0",
    )
    session.add(provenance)
    session.flush()

    result = provenance_report(session)

    assert len(result) == 1
    assert result[0]["canonical_entity_type"] == "order"


def test_sync_run_report(session):
    _make_sync_run(session)

    result = sync_run_report(session)

    assert len(result) == 1
    assert result[0]["status"] == "completed"


def test_find_missing_provenance(session):
    # Create an order without provenance
    order = Order(
        marketplace_order_id="order-1",
        status="completed",
        payment_status="paid",
        currency="IDR",
        subtotal=100000,
        shipping_cost=10000,
        discount=0,
        tax=0,
        total_amount=110000,
        platform_fee=0,
        commission=0,
        shipping_subsidy=0,
        ordered_at=datetime.now(timezone.utc),
        organization_id="org-1",
        business_id="biz-1",
        store_id="store-1",
    )
    session.add(order)
    session.flush()

    missing = find_missing_provenance(session)

    assert len(missing) == 1
    assert missing[0]["entity_type"] == "order"
    assert missing[0]["missing"] == 1


def test_payload_diff(session):
    run = _make_sync_run(session)
    _make_raw_payload(session, run.id, external_entity_id="order-1", payload_hash="hash-v1")
    _make_raw_payload(session, run.id, external_entity_id="order-1", payload_hash="hash-v2")

    result = payload_diff(session, "shopee", "store-1", "orders", "order-1")

    assert len(result) == 2
    assert result[0]["payload_hash"] == "hash-v1"
    assert result[1]["payload_hash"] == "hash-v2"
