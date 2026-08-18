"""Connector health collector.

Checks authentication, API reachability, rate-limit headroom, and last sync for
every registered connector.
"""
from commerceos.shared.value_objects.primitives import utc_now

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from commerceos.connectors.core.interfaces import ConnectorRegistry
from commerceos.monitoring.constants import Component, HealthStatus, Severity
from commerceos.monitoring.evaluators.severity import severity_from_hours, severity_from_ratio
from commerceos.monitoring.evaluators.freshness import hours_since
from commerceos.monitoring.models import HealthCheck


def collect_connector_health(
    registry: ConnectorRegistry,
    now: Optional[datetime] = None,
) -> List[HealthCheck]:
    """Collect health checks for all registered connectors."""
    now = now or utc_now()
    checks: List[HealthCheck] = []
    for code, connector in registry._connectors.items():
        health = connector.health()
        status = HealthStatus(health.status) if health.status in HealthStatus._value2member_map_ else HealthStatus.UNKNOWN

        auth_check = HealthCheck(
            component=Component.CONNECTOR.value,
            component_instance=code,
            check_type="authentication",
            status=HealthStatus.HEALTHY.value if health.authenticated else HealthStatus.UNHEALTHY.value,
            severity=Severity.INFO.value if health.authenticated else Severity.CRITICAL.value,
            message="Authenticated" if health.authenticated else "Not authenticated",
            checked_at=now,
            metadata_={"connector": code, "authenticated": health.authenticated},
        )
        checks.append(auth_check)

        api_check = HealthCheck(
            component=Component.CONNECTOR.value,
            component_instance=code,
            check_type="api_reachable",
            status=HealthStatus.HEALTHY.value if health.api_available else HealthStatus.UNHEALTHY.value,
            severity=Severity.INFO.value if health.api_available else Severity.CRITICAL.value,
            message="API reachable" if health.api_available else "API unreachable",
            checked_at=now,
            metadata_={"connector": code, "api_available": health.api_available},
        )
        checks.append(api_check)

        headroom = health.rate_limit_remaining
        headroom_pct = (headroom / 100.0) if headroom is not None else None
        rate_check = HealthCheck(
            component=Component.CONNECTOR.value,
            component_instance=code,
            check_type="rate_limit_headroom",
            status=HealthStatus.HEALTHY.value if (headroom_pct is None or headroom_pct >= 0.1) else HealthStatus.DEGRADED.value,
            severity=severity_from_ratio(headroom_pct, 0.1, 0.25).value,
            message=f"Rate limit headroom {headroom_pct*100:.1f}%" if headroom_pct is not None else "Rate limit unknown",
            checked_at=now,
            metadata_={"connector": code, "headroom_pct": headroom_pct},
        )
        checks.append(rate_check)

        last_sync = health.last_successful_sync
        sync_status = HealthStatus.HEALTHY
        if last_sync is None:
            sync_status = HealthStatus.UNKNOWN
        else:
            h = hours_since(last_sync, now)
            if h is not None and h >= 2:
                sync_status = HealthStatus.UNHEALTHY
        sync_check = HealthCheck(
            component=Component.CONNECTOR.value,
            component_instance=code,
            check_type="last_sync",
            status=sync_status.value,
            severity=severity_from_hours(last_sync, 2, 1).value,
            message=f"Last sync {hours_since(last_sync, now):.1f} hours ago" if last_sync else "No sync recorded",
            checked_at=now,
            metadata_={
                "connector": code,
                "last_successful_sync": last_sync.isoformat() if last_sync else None,
                "hours_since_sync": hours_since(last_sync, now),
            },
        )
        checks.append(sync_check)

    return checks
