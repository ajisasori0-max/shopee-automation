"""Monitoring dashboard read API.

This is the stable interface used by Streamlit and other dashboard consumers.
All reads go through MonitoringService / repositories; no direct model access.
"""
from commerceos.shared.value_objects.primitives import utc_now

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from commerceos.monitoring.constants import AlertStatus, Severity, worst_status
from commerceos.monitoring.models import Alert, HealthCheck, HealthSnapshot
from commerceos.monitoring.repositories import MonitoringUnitOfWork
from commerceos.monitoring.sqlalchemy_repositories import SQLAlchemyMonitoringUnitOfWork


class MonitoringDashboard:
    """Stable read-only dashboard API for the monitoring layer."""

    def __init__(self, uow: MonitoringUnitOfWork):
        self.uow = uow

    def get_system_health(self, since_hours: int = 24) -> Dict[str, Any]:
        """Return the latest health check per component and overall status."""
        since = utc_now() - timedelta(hours=since_hours)
        checks = self.uow.health_checks().latest_by_component()
        overall = worst_status([c.status for c in checks])
        return {
            "overall_status": overall.value,
            "checked_at": utc_now().isoformat(),
            "components": [
                {
                    "component": c.component,
                    "component_instance": c.component_instance,
                    "check_type": c.check_type,
                    "status": c.status,
                    "severity": c.severity,
                    "message": c.message,
                    "checked_at": c.checked_at.isoformat() if c.checked_at else None,
                    "metadata": c.metadata_,
                }
                for c in checks
            ],
        }

    def get_open_alerts(self) -> List[Dict[str, Any]]:
        """Return all open alerts ordered by severity."""
        alerts = self.uow.alerts().get_open()
        return [_alert_to_dict(a) for a in alerts]

    def get_recent_failures(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return recent alerts, including failures and resolutions."""
        alerts = self.uow.alerts().list_recent(limit=limit)
        return [_alert_to_dict(a) for a in alerts]

    def get_health_snapshot(self) -> Optional[Dict[str, Any]]:
        """Return the latest health snapshot."""
        snapshot = self.uow.snapshots().latest()
        if snapshot is None:
            return None
        return {
            "id": snapshot.id,
            "generated_at": snapshot.generated_at.isoformat() if snapshot.generated_at else None,
            "overall_status": snapshot.overall_status,
            "data_quality_score": float(snapshot.data_quality_score) if snapshot.data_quality_score is not None else None,
            "freshness_score": float(snapshot.freshness_score) if snapshot.freshness_score is not None else None,
            "availability_score": float(snapshot.availability_score) if snapshot.availability_score is not None else None,
            "summary": snapshot.summary,
        }


def _alert_to_dict(alert: Alert) -> Dict[str, Any]:
    return {
        "id": alert.id,
        "category": alert.category,
        "component": alert.component,
        "component_instance": alert.component_instance,
        "severity": alert.severity,
        "status": alert.status,
        "title": alert.title,
        "description": alert.description,
        "first_seen": alert.first_seen.isoformat() if alert.first_seen else None,
        "last_seen": alert.last_seen.isoformat() if alert.last_seen else None,
        "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
        "metadata": alert.metadata_,
    }


def get_system_health(uow: MonitoringUnitOfWork, since_hours: int = 24) -> Dict[str, Any]:
    return MonitoringDashboard(uow).get_system_health(since_hours=since_hours)


def get_open_alerts(uow: MonitoringUnitOfWork) -> List[Dict[str, Any]]:
    return MonitoringDashboard(uow).get_open_alerts()


def get_recent_failures(uow: MonitoringUnitOfWork, limit: int = 50) -> List[Dict[str, Any]]:
    return MonitoringDashboard(uow).get_recent_failures(limit=limit)


def get_health_snapshot(uow: MonitoringUnitOfWork) -> Optional[Dict[str, Any]]:
    return MonitoringDashboard(uow).get_health_snapshot()
