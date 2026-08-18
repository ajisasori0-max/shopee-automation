"""Tests for the COO Interface (WP3.5).

Covers:
- Intent classification
- Query routing
- Response structure and source references
- Approval awareness
- Data honesty / uncertainty when data is missing
"""

import os
from datetime import timedelta

import pytest

from commerceos.commerce.models import Inventory, Order, OrderItem, Product, Variant
from commerceos.coo.interface import COOIntentClassifier, COOInterface, ask_coo
from commerceos.platform.database.connection import create_all, get_session, reset_engine
from commerceos.shared.value_objects.primitives import utc_now


DB_URL = "sqlite:///test_coo_interface.db"


@pytest.fixture
def session():
    reset_engine()
    if os.path.exists("test_coo_interface.db"):
        os.remove("test_coo_interface.db")
    create_all(DB_URL)
    sess = get_session(DB_URL)
    try:
        yield sess
    finally:
        sess.close()
        reset_engine()
        if os.path.exists("test_coo_interface.db"):
            os.remove("test_coo_interface.db")


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
    session.add_all([product, variant, inventory, order, item])
    session.commit()
    return session


def test_intent_classification_what_matters_today():
    classifier = COOIntentClassifier()
    intent, entities = classifier.classify("What matters today?")
    assert intent == "what_matters_today"
    assert entities == {}


def test_intent_classification_what_to_approve():
    classifier = COOIntentClassifier()
    intent, entities = classifier.classify("What should I approve?")
    assert intent == "what_to_approve"


def test_intent_classification_project_history_sku():
    classifier = COOIntentClassifier()
    intent, entities = classifier.classify('What happened with SKU W-001?')
    assert intent == "project_history"
    assert "W-001" in entities.get("sku", [])


def test_intent_classification_unknown():
    classifier = COOIntentClassifier()
    intent, _ = classifier.classify("Tell me a joke")
    assert intent == "unknown"


def test_ask_what_matters_today(seeded_session):
    interface = COOInterface(seeded_session)
    response = interface.ask("What matters today?")
    assert response.intent == "what_matters_today"
    assert response.answer.startswith("**What matters today**")
    assert response.sources
    assert any(s["type"] == "decision_engine" for s in response.sources)
    assert any(s["type"] == "monitoring" for s in response.sources)


def test_ask_what_changed(seeded_session):
    interface = COOInterface(seeded_session)
    response = interface.ask("What changed this week?")
    assert response.intent == "what_changed"
    assert "Revenue" in response.answer or "no baseline" in response.answer
    assert any(s["type"] == "kpi" for s in response.sources)


def test_ask_what_to_approve(seeded_session):
    interface = COOInterface(seeded_session)
    response = interface.ask("What should I approve?")
    assert response.intent == "what_to_approve"
    assert "Pending approvals" in response.answer


def test_ask_unresolved_decisions(seeded_session):
    interface = COOInterface(seeded_session)
    response = interface.ask("What decisions are unresolved?")
    assert response.intent == "unresolved_decisions"
    assert "Unresolved decisions" in response.answer


def test_ask_help(seeded_session):
    interface = COOInterface(seeded_session)
    response = interface.ask("What can you do?")
    assert response.intent == "help"
    assert "I can answer questions" in response.answer


def test_ask_unknown(seeded_session):
    interface = COOInterface(seeded_session)
    response = interface.ask("Tell me a joke")
    assert response.intent == "unknown"
    assert response.warnings


def test_ask_coo_convenience(seeded_session):
    result = ask_coo(seeded_session, "What matters today?")
    assert result["intent"] == "what_matters_today"
    assert "answer" in result


def test_ask_project_history_missing_entity(seeded_session):
    interface = COOInterface(seeded_session)
    response = interface.ask("What happened with?")
    assert response.intent == "project_history"
    assert "Please specify" in response.answer
    assert response.warnings
