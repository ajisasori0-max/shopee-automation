"""Lightweight job execution logging helper.

Scripts and cron jobs should call `log_job_execution` at the end of a run so the
scheduler health collector can determine whether jobs are on time.
"""
from commerceos.shared.value_objects.primitives import utc_now
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from commerceos.monitoring.models import JobExecution
from commerceos.platform.database.models import new_uuid


def log_job_execution(
    session: Session,
    job_name: str,
    status: str = "completed",
    job_group: Optional[str] = None,
    started_at: Optional[datetime] = None,
    finished_at: Optional[datetime] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> JobExecution:
    """Persist a job execution record for scheduler health checks."""
    finished_at = finished_at or utc_now()
    started_at = started_at or finished_at
    duration = (finished_at - started_at).total_seconds() if started_at and finished_at else None

    record = JobExecution(
        id=new_uuid(),
        job_name=job_name,
        job_group=job_group,
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=duration,
        metadata_=metadata or {},
    )
    session.add(record)
    session.commit()
    return record


def latest_job_executions(session: Session, job_names: list[str]) -> Dict[str, datetime]:
    """Return the most recent finished_at per job name."""
    result = {}
    for name in job_names:
        record = (
            session.query(JobExecution)
            .filter_by(job_name=name)
            .order_by(JobExecution.finished_at.desc())
            .first()
        )
        if record and record.finished_at:
            result[name] = record.finished_at
    return result
