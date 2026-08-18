"""Monitoring service orchestrator.

Collects health signals from all collectors, persists them, evaluates alert
rules, deduplicates alerts, and generates health snapshots.
"""
from commerceos.shared.value_objects.primitives import utc_now

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from commerceos.connectors.core.interfaces import ConnectorRegistry
from commerceos.monitoring.collectors.commerce_state_health import collect_commerce_state_health
from commerceos.monitoring.collectors.connector_health import collect_connector_health
from commerceos.monitoring.collectors.data_quality import collect_data_quality_health
from commerceos.monitoring.collectors.kpi_health import collect_kpi_health
from commerceos.monitoring.collectors.scheduler_health import collect_scheduler_health
from commerceos.monitoring.collectors.sync_health import collect_sync_health
from commerceos.monitoring.collectors.token_health import collect_token_health
from commerceos.monitoring.constants import AlertStatus, Component, HealthStatus, Severity, worst_status
from commerceos.monitoring.evaluators.alert_rules import evaluate_rules
from commerceos.monitoring.models import Alert, HealthCheck, HealthSnapshot
from commerceos.monitoring.repositories import MonitoringUnitOfWork
from commerceos.monitoring.sqlalchemy_repositories import SQLAlchemyMonitoringUnitOfWork
from commerceos.platform.secrets import workspace_secret_manager


class MonitoringService:
    """Single operational status source for dashboards, notifications, and AI agents."""

    def __init__(
        self,
        uow: MonitoringUnitOfWork,
        session: Optional[Session] = None,
        connector_registry: Optional[ConnectorRegistry] = None,
    ):
        self.uow = uow
        self.session = session
        self.connector_registry = connector_registry or ConnectorRegistry()

    def collect_and_persist(
        self,
        store_id: Optional[str] = None,
        job_log: Optional[Dict[str, datetime]] = None,
        now: Optional[datetime] = None,
    ) -> List[HealthCheck]:
        """Run all collectors, persist health checks, and return them."""
        now = now or utc_now()
        checks: List[HealthCheck] = []

        # Collect
        checks.extend(collect_token_health(now=now))
        if self.session is not None:
            checks.extend(collect_sync_health(self.session, store_id=store_id, now=now))
            checks.extend(collect_scheduler_health(self.session, job_log=job_log, now=now))
            checks.extend(collect_kpi_health(self.session, store_id=store_id, now=now))
            checks.extend(collect_commerce_state_health(self.session, store_id=store_id, now=now))
            checks.extend(collect_data_quality_health(self.session, store_id=store_id, now=now))
        checks.extend(collect_connector_health(self.connector_registry, now=now))

        # Persist
        with self.uow:
            self.uow.health_checks().save_many(checks)

        return checks

    def evaluate_alerts(self, checks: List[HealthCheck], now: Optional[datetime] = None) -> List[Alert]:
        """Evaluate alert rules and create/update deduplicated alerts."""
        now = now or utc_now()
        candidates = evaluate_rules(checks)
        alerts: List[Alert] = []
        with self.uow:
            for candidate in candidates:
                existing = self.uow.alerts().find_matching(
                    category=str(candidate["category"]),
                    component=str(candidate["component"]),
                    component_instance=str(candidate["component_instance"]) if candidate["component_instance"] else None,
                )
                if existing:
                    existing.last_seen = now
                    existing.severity = candidate["severity"]
                    existing.description = candidate["description"]
                    existing.metadata_ = candidate["metadata"]
                    alerts.append(existing)
                else:
                    alert = Alert(
                        category=candidate["category"],
                        component=candidate["component"],
                        component_instance=candidate["component_instance"],
                        severity=candidate["severity"],
                        status=AlertStatus.OPEN.value,
                        title=candidate["title"],
                        description=candidate["description"],
                        metadata_=candidate["metadata"],
                        first_seen=now,
                        last_seen=now,
                    )
                    self.uow.alerts().save(alert)
                    alerts.append(alert)

        # Auto-resolve alerts whose conditions no longer fire
        with self.uow:
            open_alerts = self.uow.alerts().get_open()
            active_keys = {
                (c["category"], c["component"], c["component_instance"]) for c in candidates
            }
            for alert in open_alerts:
                key = (alert.category, alert.component, alert.component_instance or "")
                if key not in active_keys:
                    alert.status = AlertStatus.RESOLVED.value
                    alert.resolved_at = now

        return alerts

    def generate_snapshot(self, checks: List[HealthCheck], now: Optional[datetime] = None) -> HealthSnapshot:
        """Generate and persist an aggregated health snapshot."""
        now = now or utc_now()
        overall = worst_status([c.status for c in checks])

        dq_scores = [
            c.metadata_.get("score")
            for c in checks
            if c.check_type == "data_quality_score" and c.metadata_.get("score") is not None
        ]
        data_quality_score = sum(dq_scores) / len(dq_scores) if dq_scores else None

        freshness_checks = [
            c for c in checks if c.check_type in ("last_successful_sync", "kpi_refresh", "state_freshness", "freshness")
        ]
        fresh_count = sum(
            1 for c in freshness_checks if c.status == HealthStatus.HEALTHY.value
        )
        freshness_score = fresh_count / len(freshness_checks) if freshness_checks else None

        availability_checks = [c for c in checks if c.component in (Component.CONNECTOR.value, Component.TOKEN_MANAGER.value)]
        avail_count = sum(
            1 for c in availability_checks if c.status == HealthStatus.HEALTHY.value
        )
        availability_score = avail_count / len(availability_checks) if availability_checks else None

        summary = {
            "total_checks": len(checks),
            "by_status": _group_by(checks, lambda c: c.status),
            "by_component": _group_by(checks, lambda c: c.component),
            "by_severity": _group_by(checks, lambda c: c.severity),
        }

        snapshot = HealthSnapshot(
            generated_at=now,
            overall_status=overall.value,
            data_quality_score=round(data_quality_score, 4) if data_quality_score is not None else None,
            freshness_score=round(freshness_score, 4) if freshness_score is not None else None,
            availability_score=round(availability_score, 4) if availability_score is not None else None,
            summary=summary,
        )

        with self.uow:
            self.uow.snapshots().save(snapshot)

        return snapshot

    def run(
        self,
        store_id: Optional[str] = None,
        job_log: Optional[Dict[str, datetime]] = None,
        now: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Full monitoring run: collect, alert, snapshot."""
        checks = self.collect_and_persist(store_id=store_id, job_log=job_log, now=now)
        alerts = self.evaluate_alerts(checks, now=now)
        snapshot = self.generate_snapshot(checks, now=now)
        return {
            "checks": [c.id for c in checks],
            "alerts_open": [a.id for a in alerts if a.status == AlertStatus.OPEN.value],
            "alerts_updated": [a.id for a in alerts],
            "snapshot_id": snapshot.id,
            "overall_status": snapshot.overall_status,
        }


def _group_by(items, key_fn) -> Dict[str, int]:
    result: Dict[str, int] = {}
    for item in items:
        k = key_fn(item)
        result[k] = result.get(k, 0) + 1
    return result
