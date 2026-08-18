"""Scheduler health collector.

Checks cron job freshness by looking at recent sync runs as a proxy for scheduled
jobs. In production this should be replaced by a real cron execution log.
"""
from commerceos.shared.value_objects.primitives import utc_now

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from commerceos.ingestion.models import SyncRun
from commerceos.monitoring.constants import Component, HealthStatus, Severity
from commerceos.monitoring.evaluators.freshness import hours_since
from commerceos.monitoring.evaluators.severity import severity_from_hours
from commerceos.monitoring.job_log import latest_job_executions
from commerceos.monitoring.models import HealthCheck


# Expected cadence of scheduled jobs in hours. Keyed by job name.
# Only jobs that actually write JobExecution records via the automation runtime
# or sync/KPI scripts should be listed here. Hermes-only jobs that do not log
# executions (e.g. shopee-token-health) must not be listed, or they will
# permanently report UNKNOWN and distort the overall health status.
EXPECTED_CADENCE_HOURS = {
    "shopee-sync": 4,
    "kpi-refresh": 4,
}


def collect_scheduler_health(
    session: Session,
    job_log: Optional[Dict[str, datetime]] = None,
    now: Optional[datetime] = None,
) -> List[HealthCheck]:
    """Collect scheduler health checks.

    If ``job_log`` is provided, it maps job names to last execution times. If not,
    we infer from recent completed sync runs.
    """
    now = now or utc_now()
    checks: List[HealthCheck] = []

    job_log = dict(job_log or {})

    # Infer sync job freshness from latest completed sync run
    latest_sync = (
        session.query(SyncRun)
        .filter_by(status="completed")
        .order_by(SyncRun.completed_at.desc())
        .first()
    )
    if latest_sync and latest_sync.completed_at:
        job_log.setdefault("shopee-sync", latest_sync.completed_at)

    # Augment from persisted JobExecution records
    for name, finished_at in latest_job_executions(session, list(EXPECTED_CADENCE_HOURS.keys())).items():
        job_log.setdefault(name, finished_at)

    for job_name, expected_hours in EXPECTED_CADENCE_HOURS.items():
        last_run = job_log.get(job_name)
        h = hours_since(last_run, now)
        if h is None:
            status = HealthStatus.UNKNOWN
            severity = Severity.WARNING
            message = f"No execution record for {job_name}"
        elif h >= expected_hours * 2:
            status = HealthStatus.UNHEALTHY
            severity = Severity.CRITICAL
            message = f"Job {job_name} missed window by {h:.1f}h (expected {expected_hours}h)"
        elif h >= expected_hours:
            status = HealthStatus.DEGRADED
            severity = Severity.WARNING
            message = f"Job {job_name} late by {h:.1f}h (expected {expected_hours}h)"
        else:
            status = HealthStatus.HEALTHY
            severity = Severity.INFO
            message = f"Job {job_name} ran {h:.1f}h ago"

        checks.append(
            HealthCheck(
                component=Component.SCHEDULER.value,
                component_instance=job_name,
                check_type="cron_freshness",
                status=status.value,
                severity=severity.value,
                message=message,
                checked_at=now,
                metadata_={
                    "job_name": job_name,
                    "expected_hours": expected_hours,
                    "last_run": last_run.isoformat() if last_run else None,
                    "hours_since": h,
                },
            )
        )

    # Missed jobs count: only count degraded/unhealthy jobs that have actual records.
    # Unknown jobs (no execution log available) are not treated as missed.
    missed = [c for c in checks if c.status in (HealthStatus.DEGRADED.value, HealthStatus.UNHEALTHY.value) and c.metadata_.get("last_run") is not None]
    has_unknown = any(c.status == HealthStatus.UNKNOWN.value for c in checks)
    checks.append(
        HealthCheck(
            component=Component.SCHEDULER.value,
            component_instance="global",
            check_type="missed_job",
            status=HealthStatus.HEALTHY.value if not missed else HealthStatus.DEGRADED.value if len(missed) == 1 else HealthStatus.UNHEALTHY.value,
            severity=Severity.INFO.value if not missed else Severity.WARNING.value,
            message=f"{len(missed)} missed/late scheduled jobs" + (f"; {sum(1 for c in checks if c.status == HealthStatus.UNKNOWN.value)} jobs have no execution log" if has_unknown else ""),
            checked_at=now,
            metadata_={"missed_count": len(missed)},
        )
    )

    return checks
