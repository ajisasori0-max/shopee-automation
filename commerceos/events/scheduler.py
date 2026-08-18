"""Scheduler abstraction for recurring and one-off workflows.

Synchronous today. In production this can be backed by cron or a task queue.
"""
from commerceos.shared.value_objects.primitives import utc_now

from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from commerceos.events.constants import Priority, WorkflowJobStatus
from commerceos.events.models import WorkflowJob
from commerceos.events.sqlalchemy_repositories import SQLAlchemyEventsUnitOfWork
from commerceos.events.workflow import WorkflowEngine, register_default_workflows


class Scheduler:
    """Schedule and trigger workflow jobs."""

    def __init__(
        self,
        session: Session,
        workflow_engine: Optional[WorkflowEngine] = None,
        uow: Optional[SQLAlchemyEventsUnitOfWork] = None,
    ):
        self.session = session
        self.workflow_engine = workflow_engine or WorkflowEngine(session)
        self.uow = uow or SQLAlchemyEventsUnitOfWork(session)
        register_default_workflows(self.workflow_engine)

    def schedule_workflow(
        self,
        workflow_name: str,
        payload: Dict[str, Any],
        run_at: Optional[datetime] = None,
        priority: Priority = Priority.NORMAL,
    ) -> WorkflowJob:
        run_at = run_at or utc_now()
        return self.workflow_engine.schedule(
            workflow_name=workflow_name,
            payload=payload,
            priority=priority,
            scheduled_at=run_at,
        )

    def run_due(self, lock_manager: Optional[Any] = None) -> List[Dict[str, Any]]:
        """Execute all queued jobs that are scheduled at or before now."""
        now = utc_now()
        with self.uow:
            jobs = self.uow.workflows().get_pending(limit=100)
        due_jobs = []
        for j in jobs:
            scheduled = j.scheduled_at
            if scheduled.tzinfo is None:
                scheduled = scheduled.replace(tzinfo=timezone.utc)
            if scheduled <= now:
                due_jobs.append(j)
        results = []
        for job in due_jobs:
            results.append(self.workflow_engine.run(job.id, lock_manager=lock_manager))
        return results

    def recurring_job(
        self,
        workflow_name: str,
        payload: Dict[str, Any],
        interval_minutes: int,
        priority: Priority = Priority.NORMAL,
    ) -> WorkflowJob:
        """Schedule a one-shot job for the next interval."""
        run_at = utc_now() + timedelta(minutes=interval_minutes)
        return self.schedule_workflow(workflow_name, payload, run_at=run_at, priority=priority)
