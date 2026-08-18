"""Workflow engine for multi-step, auditable workflows.

Each workflow is a sequence of steps. Steps are executed synchronously today and
wrapped in a WorkflowJob for persistence, locking, and retry.
"""
from commerceos.shared.value_objects.primitives import utc_now

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from commerceos.events.constants import Priority, WorkflowJobStatus, is_retryable_error
from commerceos.events.locking import LockManager
from commerceos.events.models import Event, WorkflowHistory, WorkflowJob
from commerceos.events.retry import RetryManager
from commerceos.events.sqlalchemy_repositories import SQLAlchemyEventsUnitOfWork


WorkflowStep = Callable[[WorkflowJob, Dict[str, Any]], Dict[str, Any]]


class WorkflowEngine:
    """Define, schedule, and execute workflows."""

    def __init__(
        self,
        session: Session,
        uow: Optional[SQLAlchemyEventsUnitOfWork] = None,
        retry: Optional[RetryManager] = None,
    ):
        self.session = session
        self.uow = uow or SQLAlchemyEventsUnitOfWork(session)
        self.retry = retry or RetryManager()
        self._definitions: Dict[str, List[WorkflowStep]] = {}

    def define(self, workflow_name: str, steps: List[WorkflowStep]) -> None:
        self._definitions[workflow_name] = steps

    def schedule(
        self,
        workflow_name: str,
        payload: Dict[str, Any],
        priority: Priority = Priority.NORMAL,
        trigger_event: Optional[Event] = None,
        scheduled_at: Optional[datetime] = None,
    ) -> WorkflowJob:
        job = WorkflowJob(
            workflow_name=workflow_name,
            payload=payload,
            priority=priority.value,
            scheduled_at=scheduled_at or utc_now(),
            trigger_event_id=trigger_event.id if trigger_event else None,
            status=WorkflowJobStatus.QUEUED.value,
        )
        with self.uow:
            self.uow.workflows().save(job)
            self.uow.workflows().record_history(
                WorkflowHistory(job_id=job.id, old_status=None, new_status=WorkflowJobStatus.QUEUED.value)
            )
        return job

    def run(self, job_id: str, lock_manager: Optional[LockManager] = None) -> Dict[str, Any]:
        """Execute a workflow job with locking and retries."""
        with self.uow:
            job = self.uow.workflows().get(job_id)
        if job is None:
            return {"success": False, "error": "job not found"}

        steps = self._definitions.get(job.workflow_name, [])
        if not steps:
            return {"success": False, "error": f"workflow {job.workflow_name} not defined"}

        lock_name = f"workflow:{job.workflow_name}:{job.id}"
        lock_acquired = False
        if lock_manager:
            lock_acquired = lock_manager.acquire(lock_name, f"workflow-{job.id}", job_id=job.id)
            if not lock_acquired:
                return {"success": False, "error": "could not acquire lock"}

        job.status = WorkflowJobStatus.RUNNING.value
        job.started_at = utc_now()
        with self.uow:
            self.uow.workflows().save(job)
            self.uow.workflows().record_history(
                WorkflowHistory(job_id=job.id, old_status=WorkflowJobStatus.QUEUED.value, new_status=WorkflowJobStatus.RUNNING.value)
            )

        step_results = []
        final_status = WorkflowJobStatus.SUCCEEDED.value
        last_error = None
        for idx, step in enumerate(steps, start=1):
            step_name = getattr(step, "__name__", f"step_{idx}")
            try:
                result = self._run_step_with_retry(step, job)
                step_results.append({"step": step_name, "success": True, "result": result})
            except Exception as exc:
                last_error = str(exc)
                step_results.append({"step": step_name, "success": False, "error": last_error})
                final_status = WorkflowJobStatus.FAILED.value
                break

        job.status = final_status
        job.completed_at = utc_now()
        if final_status == WorkflowJobStatus.FAILED.value:
            job.retry_count += 1
        with self.uow:
            self.uow.workflows().save(job)
            self.uow.workflows().record_history(
                WorkflowHistory(
                    job_id=job.id,
                    old_status=WorkflowJobStatus.RUNNING.value,
                    new_status=final_status,
                    notes=f"steps: {len(step_results)}, error: {last_error}" if last_error else f"steps: {len(step_results)}",
                )
            )

        if lock_manager and lock_acquired:
            lock_manager.release(lock_name, f"workflow-{job.id}")

        return {
            "success": final_status == WorkflowJobStatus.SUCCEEDED.value,
            "job_id": job.id,
            "status": final_status,
            "step_results": step_results,
        }

    def _run_step_with_retry(self, step: WorkflowStep, job: WorkflowJob) -> Any:
        last_error = None
        for attempt in range(1, self.retry.max_attempts + 1):
            try:
                return step(job, job.payload)
            except Exception as exc:
                last_error = exc
                error_code = getattr(exc, "error_code", "temporary")
                if not is_retryable_error(error_code) or attempt == self.retry.max_attempts:
                    break
        raise last_error

    def attempt_retry(self, job_id: str, lock_manager: Optional[LockManager] = None) -> Dict[str, Any]:
        with self.uow:
            job = self.uow.workflows().get(job_id)
        if job is None:
            return {"success": False, "error": "job not found"}
        if job.status != WorkflowJobStatus.FAILED.value:
            return {"success": False, "error": "job is not failed"}
        job.status = WorkflowJobStatus.RETRYING.value
        with self.uow:
            self.uow.workflows().save(job)
            self.uow.workflows().record_history(
                WorkflowHistory(job_id=job.id, old_status=WorkflowJobStatus.FAILED.value, new_status=WorkflowJobStatus.RETRYING.value)
            )
        return self.run(job.id, lock_manager=lock_manager)

    def cancel(self, job_id: str) -> Dict[str, Any]:
        with self.uow:
            job = self.uow.workflows().get(job_id)
        if job is None:
            return {"success": False, "error": "job not found"}
        if job.status in {WorkflowJobStatus.SUCCEEDED.value, WorkflowJobStatus.FAILED.value, WorkflowJobStatus.CANCELLED.value}:
            return {"success": False, "error": "job already terminal"}
        old_status = job.status
        job.status = WorkflowJobStatus.CANCELLED.value
        job.completed_at = utc_now()
        with self.uow:
            self.uow.workflows().save(job)
            self.uow.workflows().record_history(
                WorkflowHistory(job_id=job.id, old_status=old_status, new_status=WorkflowJobStatus.CANCELLED.value)
            )
        return {"success": True, "job_id": job.id, "status": job.status}

    def process_queue(self, limit: int = 10, lock_manager: Optional[LockManager] = None) -> List[Dict[str, Any]]:
        """Poll and execute queued jobs. Synchronous today."""
        with self.uow:
            jobs = self.uow.workflows().get_pending(limit=limit)
        results = []
        for job in jobs:
            results.append(self.run(job.id, lock_manager=lock_manager))
        return results


# Predefined workflow steps

def step_refresh_kpis(job: WorkflowJob, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"action": "refresh_kpis", "store_id": payload.get("store_id")}


def step_refresh_commerce_state(job: WorkflowJob, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"action": "refresh_commerce_state", "store_id": payload.get("store_id")}


def step_generate_monitoring_snapshot(job: WorkflowJob, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"action": "generate_monitoring_snapshot"}


def step_generate_intelligence(job: WorkflowJob, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"action": "generate_intelligence", "store_id": payload.get("store_id")}


def step_generate_decisions(job: WorkflowJob, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"action": "generate_decisions", "store_id": payload.get("store_id")}


def register_default_workflows(engine: WorkflowEngine) -> None:
    engine.define(
        "orders_synced_pipeline",
        [
            step_refresh_kpis,
            step_refresh_commerce_state,
            step_generate_monitoring_snapshot,
            step_generate_intelligence,
            step_generate_decisions,
        ],
    )
