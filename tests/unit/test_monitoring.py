"""Unit tests for the monitoring layer."""

import datetime
from decimal import Decimal

import pytest

from commerceos.monitoring.constants import HealthStatus, Severity, worst_severity, worst_status
from commerceos.monitoring.evaluators.freshness import hours_since, is_fresh
from commerceos.monitoring.evaluators.severity import severity_from_hours, severity_from_ratio, severity_from_score
from commerceos.monitoring.models import Alert, HealthCheck, HealthSnapshot
from commerceos.monitoring.service import MonitoringService
from commerceos.monitoring.sqlalchemy_repositories import SQLAlchemyMonitoringUnitOfWork
from commerceos.platform.database.connection import create_all, get_session, reset_engine


from commerceos.monitoring.evaluators.freshness import ensure_utc


def _naive_utc(value):
    value = ensure_utc(value)
    return value.replace(tzinfo=None) if value else None


DB_URL = "sqlite:///test_monitoring_unit.db"


@pytest.fixture
def sess():
    reset_engine()
    import os

    if os.path.exists("test_monitoring_unit.db"):
        os.remove("test_monitoring_unit.db")
    create_all(DB_URL)
    session = get_session(DB_URL)
    yield session
    session.close()
    reset_engine()


@pytest.fixture
def uow(sess):
    return SQLAlchemyMonitoringUnitOfWork(sess)


class TestFreshnessEvaluators:
    def test_hours_since_naive_utc(self):
        then = datetime.datetime(2026, 7, 24, 12, 0, 0)
        now = datetime.datetime(2026, 7, 24, 15, 0, 0, tzinfo=datetime.timezone.utc)
        assert hours_since(then, now) == 3.0

    def test_is_fresh(self):
        then = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
        assert is_fresh(then, threshold_hours=2) is True
        assert is_fresh(then, threshold_hours=0.5) is False


class TestSeverityEvaluators:
    def test_severity_from_hours(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        assert severity_from_hours(now - datetime.timedelta(hours=5), 2, 1, now) == Severity.CRITICAL
        assert severity_from_hours(now - datetime.timedelta(minutes=30), 2, 1, now) == Severity.INFO
        assert severity_from_hours(None, 2, 1, now) == Severity.CRITICAL

    def test_severity_from_score(self):
        assert severity_from_score(0.4) == Severity.CRITICAL
        assert severity_from_score(0.7) == Severity.WARNING
        assert severity_from_score(0.95) == Severity.INFO

    def test_severity_from_ratio(self):
        assert severity_from_ratio(0.05) == Severity.CRITICAL
        assert severity_from_ratio(0.15) == Severity.WARNING
        assert severity_from_ratio(0.5) == Severity.INFO


class TestRankingHelpers:
    def test_worst_status(self):
        assert worst_status([HealthStatus.HEALTHY, HealthStatus.DEGRADED]) == HealthStatus.DEGRADED
        assert worst_status(["healthy", "unhealthy"]) == HealthStatus.UNHEALTHY

    def test_worst_severity(self):
        assert worst_severity([Severity.WARNING, Severity.CRITICAL]) == Severity.CRITICAL
        assert worst_severity(["info", "error"]) == Severity.ERROR


class TestMonitoringService:
    def test_empty_run_creates_snapshot(self, uow, sess):
        svc = MonitoringService(uow, session=sess)
        result = svc.run(store_id="store-001")
        assert result["snapshot_id"] is not None
        assert result["overall_status"] in [s.value for s in HealthStatus]

    def test_alert_deduplication(self, uow, sess):
        svc = MonitoringService(uow, session=sess)
        now = datetime.datetime.now(datetime.timezone.utc)
        check = HealthCheck(
            component="sync_engine",
            component_instance="store-001",
            check_type="last_successful_sync",
            status=HealthStatus.UNHEALTHY.value,
            severity=Severity.CRITICAL.value,
            metadata_={"entity_type": "orders", "hours_since_success": 5.0},
            checked_at=now,
        )
        with uow:
            uow.health_checks().save(check)
        t0 = now
        t1 = now + datetime.timedelta(minutes=5)
        alerts1 = svc.evaluate_alerts([check], now=t0)
        alerts2 = svc.evaluate_alerts([check], now=t1)
        assert len(alerts1) == 1
        assert len(alerts2) == 1
        assert alerts1[0].id == alerts2[0].id
        assert alerts2[0].last_seen >= _naive_utc(t1)

    def test_alert_auto_resolution(self, uow, sess):
        svc = MonitoringService(uow, session=sess)
        now = datetime.datetime.now(datetime.timezone.utc)
        check = HealthCheck(
            component="sync_engine",
            component_instance="store-001",
            check_type="last_successful_sync",
            status=HealthStatus.UNHEALTHY.value,
            severity=Severity.CRITICAL.value,
            metadata_={"entity_type": "orders", "hours_since_success": 5.0},
            checked_at=now,
        )
        with uow:
            uow.health_checks().save(check)
        svc.evaluate_alerts([check], now=now)
        # Healthy check should resolve the alert
        healthy_check = HealthCheck(
            component="sync_engine",
            component_instance="store-001",
            check_type="last_successful_sync",
            status=HealthStatus.HEALTHY.value,
            severity=Severity.INFO.value,
            metadata_={"entity_type": "orders", "hours_since_success": 0.5},
            checked_at=now + datetime.timedelta(minutes=10),
        )
        svc.evaluate_alerts([healthy_check], now=now + datetime.timedelta(minutes=10))
        with uow:
            open_alerts = uow.alerts().get_open()
        assert not open_alerts


class TestSnapshotGeneration:
    def test_snapshot_aggregates_scores(self, uow, sess):
        svc = MonitoringService(uow, session=sess)
        now = datetime.datetime.now(datetime.timezone.utc)
        checks = [
            HealthCheck(
                component="data_quality",
                component_instance="store-001",
                check_type="data_quality_score",
                status=HealthStatus.HEALTHY.value,
                severity=Severity.INFO.value,
                metadata_={"score": 0.95},
                checked_at=now,
            ),
            HealthCheck(
                component="sync_engine",
                component_instance="store-001",
                check_type="last_successful_sync",
                status=HealthStatus.HEALTHY.value,
                severity=Severity.INFO.value,
                metadata_={"entity_type": "orders"},
                checked_at=now,
            ),
        ]
        snapshot = svc.generate_snapshot(checks, now=now)
        assert snapshot.overall_status == HealthStatus.HEALTHY.value
        assert float(snapshot.data_quality_score) == pytest.approx(0.95)
        assert float(snapshot.freshness_score) == 1.0
