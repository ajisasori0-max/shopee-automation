"""Sync engine health collector.

Reads sync_runs and sync_checkpoints to detect last successful sync, failed syncs,
and stale checkpoints.
"""
from commerceos.shared.value_objects.primitives import utc_now

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from commerceos.ingestion.models import SyncCheckpoint, SyncRun
from commerceos.monitoring.constants import Component, HealthStatus, Severity
from commerceos.monitoring.evaluators.freshness import hours_since
from commerceos.monitoring.evaluators.severity import severity_from_hours
from commerceos.monitoring.models import HealthCheck


def collect_sync_health(
    session: Session,
    store_id: Optional[str] = None,
    now: Optional[datetime] = None,
) -> List[HealthCheck]:
    """Collect health checks for the sync engine."""
    now = now or utc_now()
    checks: List[HealthCheck] = []

    # Latest successful sync per (store, entity)
    query = session.query(SyncRun).filter_by(status="completed")
    if store_id:
        query = query.filter_by(store_id=store_id)
    completed = (
        query.order_by(SyncRun.completed_at.desc()).limit(100).all()
    )

    latest_by_scope: dict = {}
    for run in completed:
        if run.completed_at is None:
            continue
        key = (run.store_id, run.entity_type)
        if key not in latest_by_scope:
            latest_by_scope[key] = run

    for (store, entity), run in latest_by_scope.items():
        h = hours_since(run.completed_at, now)
        status = HealthStatus.HEALTHY
        if h is None or h >= 6:
            status = HealthStatus.UNHEALTHY
        elif h >= 4:
            status = HealthStatus.DEGRADED
        checks.append(
            HealthCheck(
                component=Component.SYNC_ENGINE.value,
                component_instance=store,
                check_type="last_successful_sync",
                status=status.value,
                severity=severity_from_hours(run.completed_at, 6, 4, now).value,
                message=f"Last successful {entity} sync {h:.1f} hours ago" if h is not None else "No completed sync",
                checked_at=now,
                metadata_={
                    "store_id": store,
                    "entity_type": entity,
                    "sync_run_id": run.id,
                    "hours_since_success": h,
                },
            )
        )

    # Failed syncs in the last 24 hours that are NOT superseded by a later
    # successful sync for the same (store, entity) scope. A failure that was
    # later recovered is not an active operational problem.
    recent_failed = (
        session.query(SyncRun)
        .filter_by(status="failed")
        .filter(SyncRun.created_at >= now - timedelta(hours=24))
    )
    if store_id:
        recent_failed = recent_failed.filter_by(store_id=store_id)
    failed_runs = recent_failed.all()

    # Map each scope to its latest successful sync time.
    latest_success_by_scope = {}
    for run in (
        session.query(SyncRun)
        .filter_by(status="completed")
        .filter(SyncRun.created_at >= now - timedelta(hours=24))
        .all()
    ):
        key = (run.store_id, run.entity_type)
        if run.completed_at and (key not in latest_success_by_scope or run.completed_at > latest_success_by_scope[key]):
            latest_success_by_scope[key] = run.completed_at

    unresolved_failures = [
        run for run in failed_runs
        if run.completed_at is None
        or latest_success_by_scope.get((run.store_id, run.entity_type)) is None
        or run.completed_at > latest_success_by_scope.get((run.store_id, run.entity_type))
    ]
    failed_count = len(unresolved_failures)
    failed_status = HealthStatus.HEALTHY if failed_count == 0 else HealthStatus.DEGRADED if failed_count < 3 else HealthStatus.UNHEALTHY
    checks.append(
        HealthCheck(
            component=Component.SYNC_ENGINE.value,
            component_instance=store_id or "global",
            check_type="failed_syncs",
            status=failed_status.value,
            severity=Severity.INFO.value if failed_count == 0 else Severity.WARNING.value if failed_count < 3 else Severity.ERROR.value,
            message=f"{failed_count} unresolved failed sync runs in last 24h ({len(failed_runs)} total failures)",
            checked_at=now,
            metadata_={"failed_count": failed_count, "total_failed_count": len(failed_runs), "window_hours": 24},
        )
    )

    # Stale checkpoints
    checkpoint_query = session.query(SyncCheckpoint)
    if store_id:
        checkpoint_query = checkpoint_query.filter_by(store_id=store_id)
    checkpoints = checkpoint_query.all()
    stale_count = 0
    for cp in checkpoints:
        h = hours_since(cp.last_successful_sync_at, now)
        if h is not None and h >= 24:
            stale_count += 1
    checks.append(
        HealthCheck(
            component=Component.SYNC_ENGINE.value,
            component_instance=store_id or "global",
            check_type="stale_checkpoints",
            status=HealthStatus.HEALTHY.value if stale_count == 0 else HealthStatus.DEGRADED.value,
            severity=Severity.INFO.value if stale_count == 0 else Severity.WARNING.value,
            message=f"{stale_count} stale checkpoints (>=24h)",
            checked_at=now,
            metadata_={"stale_count": stale_count, "total_checkpoints": len(checkpoints)},
        )
    )

    return checks


from datetime import timedelta  # noqa: E402
