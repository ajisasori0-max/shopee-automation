"""Health reporting for the automation runtime."""


from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from commerceos.jobs.registry import JobRegistry
from commerceos.monitoring.models import JobExecution
from commerceos.shared.value_objects.primitives import utc_now


class JobHealthReporter:
    """Summarize recent job execution health."""

    def __init__(self, session: Session, registry: Optional[JobRegistry] = None):
        self.session = session
        self.registry = registry

    def recent_failures(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Return job executions that failed in the last N hours."""
        since = utc_now() - timedelta(hours=hours)
        rows = (
            self.session.query(JobExecution)
            .filter(JobExecution.status == "failed")
            .filter(JobExecution.finished_at >= since)
            .order_by(JobExecution.finished_at.desc())
            .all()
        )
        return [
            {
                "job_name": r.job_name,
                "job_group": r.job_group,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                "metadata": r.metadata_,
            }
            for r in rows
        ]

    def overdue_jobs(self, expected_intervals: Dict[str, int]) -> List[Dict[str, Any]]:
        """Return registered jobs whose latest run is older than expected (hours)."""
        overdue = []
        names = self.registry.names() if self.registry else list(expected_intervals.keys())
        for name in names:
            interval = expected_intervals.get(name)
            if interval is None:
                continue
            latest = (
                self.session.query(JobExecution)
                .filter_by(job_name=name)
                .order_by(JobExecution.finished_at.desc())
                .first()
            )
            if latest is None or latest.finished_at is None:
                overdue.append({"name": name, "hours_since": None, "threshold_hours": interval})
                continue
            hours_since = (utc_now() - latest.finished_at).total_seconds() / 3600
            if hours_since > interval:
                overdue.append({"name": name, "hours_since": round(hours_since, 1), "threshold_hours": interval})
        return overdue

    def summary(self, hours: int = 24) -> Dict[str, Any]:
        """Overall runtime health summary."""
        since = utc_now() - timedelta(hours=hours)
        total = (
            self.session.query(JobExecution)
            .filter(JobExecution.finished_at >= since)
            .count()
        )
        failed = (
            self.session.query(JobExecution)
            .filter(JobExecution.status == "failed")
            .filter(JobExecution.finished_at >= since)
            .count()
        )
        return {
            "window_hours": hours,
            "total_executions": total,
            "failed_executions": failed,
            "healthy": failed == 0 and total > 0,
            "failures": self.recent_failures(hours),
        }
