"""Integration tests for the Decision Engine."""

import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from commerceos.commerce.models import KPI, CommerceState
from commerceos.decision.approval import ApprovalWorkflow
from commerceos.decision.constants import DecisionCategory, DecisionSeverity, DecisionStatus
from commerceos.decision.dashboard import DecisionDashboard, get_high_priority, get_open_decisions, get_decision_summary
from commerceos.decision.engine import DecisionEngine, DecisionLifecycleService
from commerceos.decision.models import Decision
from commerceos.decision.sqlalchemy_repositories import SQLAlchemyDecisionUnitOfWork, sqlalchemy_decision_uow
from commerceos.platform.database.connection import create_all, get_session, reset_engine
from commerceos.platform.database.models import new_uuid


DB_URL = "sqlite:///test_decision_integration.db"


@pytest.fixture
def sess():
    reset_engine()
    if os.path.exists("test_decision_integration.db"):
        os.remove("test_decision_integration.db")
    create_all(DB_URL)
    session = get_session(DB_URL)
    yield session
    session.close()
    reset_engine()


@pytest.fixture
def uow(sess):
    return SQLAlchemyDecisionUnitOfWork(sess)


def _make_kpi(sess, code, value, freshness, store_id="store-001"):
    kpi = KPI(
        id=new_uuid(),
        code=code,
        name=code.replace("_", " ").title(),
        value=Decimal(str(value)),
        confidence=Decimal("1.0"),
        freshness=freshness,
        organization_id="org-001",
        business_id="biz-001",
        store_id=store_id,
    )
    sess.add(kpi)
    sess.commit()
    return kpi


class TestDecisionEngine:
    def test_refresh_creates_decisions(self, uow, sess):
        base = datetime(2026, 7, 24, 0, 0, 0, tzinfo=timezone.utc)
        _make_kpi(sess, "roas", 1.5, base)
        _make_kpi(sess, "ad_spend", 100, base)
        _make_kpi(sess, "gross_margin_pct", 0.05, base)
        _make_kpi(sess, "cash_balance", 15_000_000, base)

        engine = DecisionEngine(sess, uow=uow)
        insights = [{"category": "advertising", "title": "ROAS fell", "explanation": "ROAS 1.5"}]
        result = engine.refresh("store-001", insights=insights)

        assert result["decision_count"] >= 1

    def test_decision_lifecycle(self, uow, sess):
        engine = DecisionEngine(sess, uow=uow)
        base = datetime(2026, 7, 24, 0, 0, 0, tzinfo=timezone.utc)
        _make_kpi(sess, "roas", 1.5, base)
        _make_kpi(sess, "ad_spend", 100, base)
        result = engine.refresh("store-001", insights=[{"category": "advertising", "title": "ROAS fell", "explanation": "ROAS 1.5"}])
        decision_id = result["decisions"][0]["id"]

        lifecycle = DecisionLifecycleService(uow)
        lifecycle.approve(decision_id, changed_by="tester")
        with uow:
            d = uow.decisions().get(decision_id)
            assert d.status == DecisionStatus.APPROVED.value

        lifecycle.record_execution(decision_id, changed_by="tester")
        with uow:
            d = uow.decisions().get(decision_id)
            assert d.status == DecisionStatus.EXECUTED.value

    def test_dashboard_api(self, uow, sess):
        engine = DecisionEngine(sess, uow=uow)
        base = datetime(2026, 7, 24, 0, 0, 0, tzinfo=timezone.utc)
        _make_kpi(sess, "roas", 1.5, base)
        _make_kpi(sess, "ad_spend", 100, base)
        engine.refresh("store-001", insights=[{"category": "advertising", "title": "ROAS fell", "explanation": "ROAS 1.5"}])

        open_d = get_open_decisions(uow)
        assert open_d
        high = get_high_priority(uow, limit=5)
        assert high
        summary = get_decision_summary(uow)
        assert summary["counts_by_status"]["proposed"] >= 1

    def test_evidence_persisted(self, uow, sess):
        engine = DecisionEngine(sess, uow=uow)
        base = datetime(2026, 7, 24, 0, 0, 0, tzinfo=timezone.utc)
        _make_kpi(sess, "roas", 1.5, base)
        _make_kpi(sess, "ad_spend", 100, base)
        result = engine.refresh("store-001", insights=[{"category": "advertising", "title": "ROAS fell", "explanation": "ROAS 1.5"}])
        decision_id = result["decisions"][0]["id"]

        with uow:
            decision = uow.decisions().get(decision_id)
            assert decision.evidence
