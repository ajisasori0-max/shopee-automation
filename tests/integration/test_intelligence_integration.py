"""Integration tests for the decision intelligence layer."""

import datetime
import os
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from commerceos.commerce.models import CommerceState, KPI
from commerceos.intelligence.constants import InsightCategory, InsightSeverity, TrendPeriod
from commerceos.intelligence.dashboard import get_business_summary, get_daily_insights, get_priority_insights, get_trend_summary
from commerceos.intelligence.engine import IntelligenceEngine
from commerceos.intelligence.models import Insight, TrendSnapshot
from commerceos.intelligence.sqlalchemy_repositories import SQLAlchemyIntelligenceUnitOfWork, sqlalchemy_intelligence_uow
from commerceos.platform.database.connection import create_all, get_session, reset_engine
from commerceos.platform.database.models import new_uuid


DB_URL = "sqlite:///test_intelligence_integration.db"


@pytest.fixture
def sess():
    reset_engine()
    if os.path.exists("test_intelligence_integration.db"):
        os.remove("test_intelligence_integration.db")
    create_all(DB_URL)
    session = get_session(DB_URL)
    yield session
    session.close()
    reset_engine()


@pytest.fixture
def uow(sess):
    return SQLAlchemyIntelligenceUnitOfWork(sess)


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


class TestIntelligenceEngine:
    def test_refresh_creates_insights_and_trends(self, uow, sess):
        base = datetime.datetime(2026, 7, 24, 0, 0, 0, tzinfo=datetime.timezone.utc)
        # Create two days of revenue data
        _make_kpi(sess, "gross_sales", 100, base - datetime.timedelta(days=1))
        _make_kpi(sess, "gross_sales", 150, base)
        _make_kpi(sess, "order_count", 10, base - datetime.timedelta(days=1))
        _make_kpi(sess, "order_count", 10, base)
        _make_kpi(sess, "aov", 10, base - datetime.timedelta(days=1))
        _make_kpi(sess, "aov", 15, base)
        _make_kpi(sess, "gross_profit", 50, base - datetime.timedelta(days=1))
        _make_kpi(sess, "gross_profit", 75, base)
        _make_kpi(sess, "gross_margin_pct", 0.5, base - datetime.timedelta(days=1))
        _make_kpi(sess, "gross_margin_pct", 0.5, base)
        _make_kpi(sess, "ad_spend", 20, base - datetime.timedelta(days=1))
        _make_kpi(sess, "ad_spend", 20, base)
        _make_kpi(sess, "roas", 2.5, base - datetime.timedelta(days=1))
        _make_kpi(sess, "roas", 2.5, base)

        engine = IntelligenceEngine(sess, uow=uow)
        result = engine.refresh(store_id="store-001", reference_date=base.date())

        assert result["insight_count"] >= 1
        assert result["trend_count"] >= 1

        with uow:
            insights = uow.insights().list(limit=100)
            trends = uow.trends().list(limit=100)
        assert insights
        assert trends

    def test_revenue_anomaly_insight(self, uow, sess):
        base = datetime.datetime(2026, 7, 24, 0, 0, 0, tzinfo=datetime.timezone.utc)
        _make_kpi(sess, "gross_sales", 100, base - datetime.timedelta(days=1))
        _make_kpi(sess, "gross_sales", 150, base)
        _make_kpi(sess, "order_count", 10, base - datetime.timedelta(days=1))
        _make_kpi(sess, "order_count", 10, base)
        _make_kpi(sess, "aov", 10, base - datetime.timedelta(days=1))
        _make_kpi(sess, "aov", 15, base)

        engine = IntelligenceEngine(sess, uow=uow)
        engine.refresh(store_id="store-001", reference_date=base.date())

        with uow:
            insights = uow.insights().list(category=InsightCategory.REVENUE.value)
        assert insights
        assert any("50.0%" in i.title or "50%" in i.title for i in insights)

    def test_dashboard_api(self, uow, sess):
        base = datetime.datetime(2026, 7, 24, 0, 0, 0, tzinfo=datetime.timezone.utc)
        _make_kpi(sess, "gross_sales", 100, base - datetime.timedelta(days=1))
        _make_kpi(sess, "gross_sales", 150, base)

        engine = IntelligenceEngine(sess, uow=uow)
        engine.refresh(store_id="store-001", reference_date=base.date())

        daily = get_daily_insights(uow)
        assert daily
        priority = get_priority_insights(uow)
        assert priority
        trends = get_trend_summary(uow)
        assert trends
        summary = get_business_summary(uow)
        assert summary["overall_severity"] in [s.value for s in InsightSeverity]
