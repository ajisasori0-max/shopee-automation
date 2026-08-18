"""Integration tests for the monitoring layer against real data patterns."""

import datetime
import os
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from commerceos.commerce.models import CommerceState, KPI, Order, Payment
from commerceos.ingestion.models import SyncRun, SyncCheckpoint
from commerceos.monitoring.constants import HealthStatus, Severity
from commerceos.monitoring.models import Alert, HealthCheck
from commerceos.monitoring.service import MonitoringService
from commerceos.monitoring.sqlalchemy_repositories import SQLAlchemyMonitoringUnitOfWork
from commerceos.platform.database.connection import create_all, get_session, reset_engine
from commerceos.platform.database.models import new_uuid


DB_URL = "sqlite:///test_monitoring_integration.db"


@pytest.fixture
def sess():
    reset_engine()
    if os.path.exists("test_monitoring_integration.db"):
        os.remove("test_monitoring_integration.db")
    create_all(DB_URL)
    session = get_session(DB_URL)
    yield session
    session.close()
    reset_engine()


@pytest.fixture
def uow(sess):
    return SQLAlchemyMonitoringUnitOfWork(sess)


def _make_sync_run(sess, entity_type, status, completed_at, store_id="store-001"):
    run = SyncRun(
        id=new_uuid(),
        connector_code="shopee",
        store_id=store_id,
        entity_type=entity_type,
        sync_mode="incremental",
        connector_version="1.0.0",
        status=status,
        records_received=10,
        records_persisted=10,
        records_failed=0,
        completed_at=completed_at,
        started_at=completed_at - datetime.timedelta(minutes=1),
    )
    sess.add(run)
    sess.commit()
    return run


class TestFailedSyncAlert:
    def test_failed_sync_generates_alert(self, uow, sess):
        now = datetime.datetime.now(datetime.timezone.utc)
        _make_sync_run(sess, "orders", "failed", now - datetime.timedelta(minutes=10))
        svc = MonitoringService(uow, session=sess)
        svc.run(store_id="store-001", now=now)
        with uow:
            open_alerts = uow.alerts().get_open(component="sync_engine")
        assert any(a.severity in (Severity.WARNING.value, Severity.CRITICAL.value, Severity.ERROR.value) for a in open_alerts)


class TestMissingKPIAlert:
    def test_missing_kpi_generates_alert(self, uow, sess):
        now = datetime.datetime.now(datetime.timezone.utc)
        svc = MonitoringService(uow, session=sess)
        svc.run(store_id="store-001", now=now)
        with uow:
            open_alerts = uow.alerts().get_open(component="kpi_engine")
        assert any("missing" in a.title.lower() or "refresh" in a.title.lower() for a in open_alerts)


class TestStaleCommerceStateAlert:
    def test_stale_commerce_state_generates_alert(self, uow, sess):
        now = datetime.datetime.now(datetime.timezone.utc)
        stale_state = CommerceState(
            id=new_uuid(),
            version="1",
            valid_until=now - datetime.timedelta(hours=1),
            data_quality_score=Decimal("1.0"),
            confidence_level="high",
            sources_fresh=[],
            sources_stale=[],
            summary={},
            alerts=[],
            risks=[],
            opportunities=[],
            anomalies=[],
            todays_focus={},
            last_sync={},
            data_quality={},
            organization_id="org-001",
            business_id="biz-001",
            store_id="store-001",
            created_at=now - datetime.timedelta(hours=5),
            updated_at=now - datetime.timedelta(hours=5),
        )
        sess.add(stale_state)
        sess.commit()
        svc = MonitoringService(uow, session=sess)
        svc.run(store_id="store-001", now=now)
        with uow:
            open_alerts = uow.alerts().get_open(component="commerce_state")
        assert any("older" in a.title.lower() or "commerce state" in a.title.lower() for a in open_alerts)


class TestFreshCommerceStateNoAlert:
    def test_fresh_commerce_state_no_state_alert(self, uow, sess):
        now = datetime.datetime.now(datetime.timezone.utc)
        fresh_state = CommerceState(
            id=new_uuid(),
            version="1",
            valid_until=now + datetime.timedelta(hours=1),
            data_quality_score=Decimal("1.0"),
            confidence_level="high",
            sources_fresh=["orders"],
            sources_stale=[],
            summary={},
            alerts=[],
            risks=[],
            opportunities=[],
            anomalies=[],
            todays_focus={},
            last_sync={},
            data_quality={},
            organization_id="org-001",
            business_id="biz-001",
            store_id="store-001",
            created_at=now,
            updated_at=now,
        )
        sess.add(fresh_state)
        sess.commit()
        svc = MonitoringService(uow, session=sess)
        svc.run(store_id="store-001", now=now)
        with uow:
            open_alerts = uow.alerts().get_open(component="commerce_state")
        assert not open_alerts
