"""Deterministic alert rules for the monitoring layer.

Rules translate health checks into alert candidates. The MonitoringService is
responsible for deduplicating and persisting them.
"""

from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional

from commerceos.monitoring.constants import AlertCategory, Component, Severity
from commerceos.monitoring.models import HealthCheck
from commerceos.monitoring.evaluators.freshness import hours_since


class AlertRule:
    """One deterministic alert rule."""

    def __init__(
        self,
        category: AlertCategory,
        component: Component,
        check_type: str,
        title_template: str,
        description_template: str,
        severity: Severity,
        condition,
    ):
        self.category = category
        self.component = component
        self.check_type = check_type
        self.title_template = title_template
        self.description_template = description_template
        self.severity = severity
        self.condition = condition

    def applies_to(self, check: HealthCheck) -> bool:
        return (
            check.component == self.component.value
            and check.check_type == self.check_type
            and self.condition(check)
        )

    def render(self, check: HealthCheck) -> Dict[str, object]:
        metadata = defaultdict(str)
        metadata.update(check.metadata_ or {})
        metadata.setdefault("check_id", check.id)
        metadata.setdefault("status", check.status)
        metadata.setdefault("component_instance", check.component_instance or "")
        return {
            "category": self.category.value,
            "component": self.component.value,
            "component_instance": check.component_instance or "",
            "severity": self.severity.value,
            "title": self.title_template.format_map(metadata),
            "description": self.description_template.format_map(metadata),
            "metadata": dict(metadata),
        }


RULES: List[AlertRule] = [
    AlertRule(
        category=AlertCategory.SYNC,
        component=Component.SYNC_ENGINE,
        check_type="last_successful_sync",
        title_template="No successful sync in >2 hours",
        description_template="Entity {entity_type} for store {component_instance} has not synced successfully in the last 2 hours.",
        severity=Severity.CRITICAL,
        condition=lambda c: bool(
            c.status in ("unhealthy", "degraded")
            and c.metadata_.get("hours_since_success")
            and c.metadata_.get("hours_since_success", 0) >= 2
        ),
    ),
    AlertRule(
        category=AlertCategory.TOKEN,
        component=Component.TOKEN_MANAGER,
        check_type="token_expiry",
        title_template="Token expires in <24h",
        description_template="{token_type} token for store {component_instance} expires in {hours_remaining:.1f} hours.",
        severity=Severity.WARNING,
        condition=lambda c: bool(
            c.status in ("degraded", "unhealthy")
            and c.metadata_.get("hours_remaining") is not None
            and c.metadata_.get("hours_remaining", 0) < 24
        ),
    ),
    AlertRule(
        category=AlertCategory.DATA_QUALITY,
        component=Component.DATA_QUALITY,
        check_type="data_quality_score",
        title_template="Data quality score below 0.8",
        description_template="Data quality score for store {component_instance} is {score:.2f}.",
        severity=Severity.WARNING,
        condition=lambda c: bool(
            c.metadata_.get("score") is not None and c.metadata_.get("score", 1.0) < 0.8
        ),
    ),
    AlertRule(
        category=AlertCategory.COMMERCE_STATE,
        component=Component.COMMERCE_STATE,
        check_type="state_freshness",
        title_template="Commerce State older than 2 hours",
        description_template="Commerce State for store {component_instance} was generated {hours_since:.1f} hours ago.",
        severity=Severity.CRITICAL,
        condition=lambda c: bool(
            c.status in ("unhealthy", "degraded")
            and c.metadata_.get("hours_since") is not None
            and c.metadata_.get("hours_since", 0) >= 2
        ),
    ),
    AlertRule(
        category=AlertCategory.KPI,
        component=Component.KPI_ENGINE,
        check_type="kpi_refresh",
        title_template="KPI refresh failed",
        description_template="KPI refresh for store {component_instance} failed or has not run.",
        severity=Severity.CRITICAL,
        condition=lambda c: bool(c.status == "unhealthy"),
    ),
    AlertRule(
        category=AlertCategory.CONNECTOR,
        component=Component.CONNECTOR,
        check_type="rate_limit_headroom",
        title_template="Connector rate limit headroom below 10%",
        description_template="{connector} rate limit headroom for store {component_instance} is {headroom_pct:.1f}%.",
        severity=Severity.WARNING,
        condition=lambda c: bool(
            c.metadata_.get("headroom_pct") is not None and c.metadata_.get("headroom_pct", 1.0) < 10.0
        ),
    ),
    AlertRule(
        category=AlertCategory.SCHEDULER,
        component=Component.SCHEDULER,
        check_type="missed_job",
        title_template="Scheduler missed job",
        description_template="Scheduled job {job_name} missed its expected window.",
        severity=Severity.WARNING,
        condition=lambda c: bool(c.status in ("unhealthy", "degraded")),
    ),
    AlertRule(
        category=AlertCategory.SYNC,
        component=Component.SYNC_ENGINE,
        check_type="failed_syncs",
        title_template="Failed sync runs in last 24h",
        description_template="{failed_count} sync runs failed in the last 24 hours.",
        severity=Severity.WARNING,
        condition=lambda c: bool(
            c.status in ("unhealthy", "degraded")
            and c.metadata_.get("failed_count", 0) > 0
        ),
    ),
]


def evaluate_rules(checks: List[HealthCheck]) -> List[Dict[str, object]]:
    """Evaluate all rules against a list of health checks and return alert candidates."""
    alerts: List[Dict[str, object]] = []
    for check in checks:
        for rule in RULES:
            if rule.applies_to(check):
                alerts.append(rule.render(check))
    return alerts
