"""Job runner for the automation runtime.

Executes registered jobs, persists execution history, handles failures, and
exposes health/status queries. No scheduling logic — callers decide when to run.
"""
from __future__ import annotations
from commerceos.shared.value_objects.primitives import utc_now


import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from commerceos.jobs.registry import JobDefinition, JobRegistry
from commerceos.monitoring.job_log import log_job_execution
from commerceos.monitoring.models import JobExecution
from commerceos.platform.database.models import new_uuid


class JobRunner:
    """Execute jobs and record their outcomes."""

    def __init__(self, session: Session, registry: Optional[JobRegistry] = None):
        self.session = session
        self.registry = registry or JobRegistry()

    def run(
        self,
        name: str,
        *args,
        **kwargs,
    ) -> Dict[str, Any]:
        """Run a single job by name and persist execution history.

        Returns a dict with the job result, status, and execution id.
        """
        definition = self.registry.get(name)
        if definition is None:
            return {
                "name": name,
                "status": "failed",
                "error": f"Job '{name}' is not registered",
                "execution_id": None,
            }

        handler = self.registry.get_handler(name)
        if handler is None:
            return {
                "name": name,
                "status": "failed",
                "error": f"Job '{name}' has no handler",
                "execution_id": None,
            }

        started_at = utc_now()
        metadata: Dict[str, Any] = {
            "idempotency_key": definition.idempotency_key() if definition.idempotency_key else None,
        }
        result: Any = None
        status = "completed"
        error: Optional[str] = None

        try:
            # Handlers receive the runner's session as the first argument.
            result = handler(self.session, *args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            status = "failed"
            error = f"{exc.__class__.__name__}: {exc}"
            metadata["traceback"] = traceback.format_exc()
            # Roll back the runner's session so the job execution log can be
            # committed independently. If the handler already committed, the
            # rollback is a no-op for those changes but clears any failed
            # pending state.
            try:
                self.session.rollback()
            except Exception as rollback_exc:  # noqa: BLE001
                metadata["rollback_error"] = f"{rollback_exc.__class__.__name__}: {rollback_exc}"

        finished_at = utc_now()
        metadata["result"] = result if isinstance(result, (dict, list, str, int, float, bool, type(None))) else str(result)
        if error:
            metadata["error"] = error

        execution = log_job_execution(
            session=self.session,
            job_name=name,
            job_group=definition.group,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            metadata=metadata,
        )

        return {
            "name": name,
            "status": status,
            "error": error,
            "execution_id": execution.id,
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "result": result,
        }

    def run_many(self, names: List[str], *args, **kwargs) -> List[Dict[str, Any]]:
        """Run a list of jobs sequentially."""
        return [self.run(name, *args, **kwargs) for name in names]

    def latest_status(self, name: str) -> Optional[Dict[str, Any]]:
        """Return the latest execution status for a job."""
        execution = (
            self.session.query(JobExecution)
            .filter_by(job_name=name)
            .order_by(JobExecution.finished_at.desc())
            .first()
        )
        if execution is None:
            return None
        return {
            "name": execution.job_name,
            "status": execution.status,
            "finished_at": execution.finished_at.isoformat() if execution.finished_at else None,
            "duration_seconds": execution.duration_seconds,
            "metadata": execution.metadata_,
        }

    def health_summary(self) -> List[Dict[str, Any]]:
        """Return latest status for every registered job."""
        return [self.latest_status(name) or {"name": name, "status": "never_run"} for name in self.registry.names()]
