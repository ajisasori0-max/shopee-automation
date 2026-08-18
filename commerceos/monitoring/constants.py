"""Shared enumerations and status helpers for the monitoring layer."""

from enum import Enum


class HealthStatus(str, Enum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"


class AlertCategory(str, Enum):
    SYNC = "sync"
    TOKEN = "token"
    CONNECTOR = "connector"
    KPI = "kpi"
    COMMERCE_STATE = "commerce_state"
    DATA_QUALITY = "data_quality"
    SCHEDULER = "scheduler"


class Component(str, Enum):
    CONNECTOR = "connector"
    SYNC_ENGINE = "sync_engine"
    KPI_ENGINE = "kpi_engine"
    COMMERCE_STATE = "commerce_state"
    SCHEDULER = "scheduler"
    TOKEN_MANAGER = "token_manager"
    DATA_QUALITY = "data_quality"


def status_rank(status: HealthStatus) -> int:
    """Lower number = better health.

    UNKNOWN is the least severe status because it means we simply have no
    signal yet; it must not override a concrete DEGRADED or UNHEALTHY result.
    """
    return {
        HealthStatus.HEALTHY: 0,
        HealthStatus.UNKNOWN: 1,
        HealthStatus.DEGRADED: 2,
        HealthStatus.UNHEALTHY: 3,
    }.get(status, 4)


def severity_rank(severity: Severity) -> int:
    """Higher number = more severe."""
    return {
        Severity.INFO: 0,
        Severity.WARNING: 1,
        Severity.ERROR: 2,
        Severity.CRITICAL: 3,
    }.get(severity, 0)


def worst_severity(severities) -> Severity:
    """Return the most severe value from a list of Severity strings/enums."""
    ranked = sorted(
        [Severity(s) if isinstance(s, str) else s for s in severities if s],
        key=severity_rank,
        reverse=True,
    )
    return ranked[0] if ranked else Severity.INFO


def worst_status(statuses) -> HealthStatus:
    """Return the worst health status from a list of HealthStatus strings/enums."""
    ranked = sorted(
        [HealthStatus(s) if isinstance(s, str) else s for s in statuses if s],
        key=status_rank,
        reverse=True,
    )
    return ranked[0] if ranked else HealthStatus.UNKNOWN
