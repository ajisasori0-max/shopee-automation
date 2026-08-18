"""Data quality health collector.

Checks freshness, reconciliation failures, validation failures, and missing
provenance.
"""
from commerceos.shared.value_objects.primitives import utc_now

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from commerceos.commerce.models import DataQualityEvent, ReconciliationEvent
from commerceos.ingestion.audit import find_missing_provenance
from commerceos.ingestion.models import SyncCheckpoint
from commerceos.monitoring.constants import Component, HealthStatus, Severity
from commerceos.monitoring.evaluators.freshness import hours_since
from commerceos.monitoring.evaluators.severity import severity_from_hours, severity_from_score
from commerceos.monitoring.models import HealthCheck


def collect_data_quality_health(
    session: Session,
    store_id: Optional[str] = None,
    now: Optional[datetime] = None,
) -> List[HealthCheck]:
    """Collect data quality health checks."""
    now = now or utc_now()
    checks: List[HealthCheck] = []

    # Freshness of latest raw payload or checkpoint
    latest_checkpoint = (
        session.query(SyncCheckpoint)
        .filter_by(store_id=store_id)
        .order_by(SyncCheckpoint.last_successful_sync_at.desc())
        .first()
        if store_id
        else session.query(SyncCheckpoint).order_by(SyncCheckpoint.last_successful_sync_at.desc()).first()
    )
    h = hours_since(latest_checkpoint.last_successful_sync_at if latest_checkpoint else None, now)
    checks.append(
        HealthCheck(
            component=Component.DATA_QUALITY.value,
            component_instance=store_id or "global",
            check_type="freshness",
            status=HealthStatus.HEALTHY.value if h is not None and h < 24 else HealthStatus.DEGRADED.value if h is not None else HealthStatus.UNHEALTHY.value,
            severity=severity_from_hours(latest_checkpoint.last_successful_sync_at if latest_checkpoint else None, 24, 2, now).value,
            message=f"Latest data source {h:.1f} hours ago" if h is not None else "No data source activity recorded",
            checked_at=now,
            metadata_={
                "store_id": store_id,
                "hours_since": h,
                "checkpoint_id": latest_checkpoint.id if latest_checkpoint else None,
            },
        )
    )

    # Reconciliation failures
    rec_query = session.query(ReconciliationEvent).filter(
        ReconciliationEvent.status.in_(["open", "failed"]),
        ReconciliationEvent.created_at >= now - timedelta(hours=24),
    )
    if store_id:
        rec_query = rec_query.filter_by(store_id=store_id)
    rec_count = rec_query.count()
    checks.append(
        HealthCheck(
            component=Component.DATA_QUALITY.value,
            component_instance=store_id or "global",
            check_type="reconciliation_failures",
            status=HealthStatus.HEALTHY.value if rec_count == 0 else HealthStatus.DEGRADED.value,
            severity=Severity.INFO.value if rec_count == 0 else Severity.WARNING.value,
            message=f"{rec_count} reconciliation failures in last 24h",
            checked_at=now,
            metadata_={"store_id": store_id, "failure_count": rec_count},
        )
    )

    # Validation failures (data quality events)
    dq_query = session.query(DataQualityEvent).filter(
        DataQualityEvent.resolved_at.is_(None),
        DataQualityEvent.created_at >= now - timedelta(hours=24),
    )
    if store_id:
        dq_query = dq_query.filter_by(store_id=store_id)
    dq_count = dq_query.count()
    checks.append(
        HealthCheck(
            component=Component.DATA_QUALITY.value,
            component_instance=store_id or "global",
            check_type="validation_failures",
            status=HealthStatus.HEALTHY.value if dq_count == 0 else HealthStatus.DEGRADED.value,
            severity=Severity.INFO.value if dq_count == 0 else Severity.WARNING.value,
            message=f"{dq_count} unresolved data quality events in last 24h",
            checked_at=now,
            metadata_={"store_id": store_id, "event_count": dq_count},
        )
    )

    # Missing provenance
    missing_prov = find_missing_provenance(session)
    if store_id:
        missing_prov = [m for m in missing_prov if m.get("store_id") == store_id]
    total_missing = sum(m["missing"] for m in missing_prov)
    score = 1.0 if total_missing == 0 else max(0.0, 1.0 - (total_missing / 100.0))
    checks.append(
        HealthCheck(
            component=Component.DATA_QUALITY.value,
            component_instance=store_id or "global",
            check_type="data_quality_score",
            status=HealthStatus.HEALTHY.value if score >= 0.8 else HealthStatus.DEGRADED.value if score >= 0.5 else HealthStatus.UNHEALTHY.value,
            severity=severity_from_score(score, 0.5, 0.8).value,
            message=f"Data quality score {score:.2f} ({total_missing} missing provenance records)",
            checked_at=now,
            metadata_={
                "store_id": store_id,
                "score": score,
                "missing_provenance": total_missing,
                "details": missing_prov,
            },
        )
    )

    return checks
