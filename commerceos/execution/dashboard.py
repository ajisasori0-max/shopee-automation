"""Execution Engine dashboard read API.

Stable interface for Streamlit and other dashboard consumers. No direct SQLAlchemy
model access.
"""
from commerceos.shared.value_objects.primitives import utc_now

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from commerceos.execution.constants import ExecutionStatus
from commerceos.execution.models import ExecutionPlan
from commerceos.execution.repositories import ExecutionUnitOfWork


class ExecutionDashboard:
    """Stable read-only dashboard API for the execution layer."""

    def __init__(self, uow: ExecutionUnitOfWork):
        self.uow = uow

    def get_execution_queue(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return plans ready or planned to execute, ordered by creation."""
        plans = self.uow.plans().list(status=ExecutionStatus.READY.value, limit=limit)
        if len(plans) < limit:
            planned = self.uow.plans().list(status=ExecutionStatus.PLANNED.value, limit=limit - len(plans))
            plans.extend(planned)
        return [_plan_to_dict(p) for p in plans]

    def get_running(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return currently running plans."""
        plans = self.uow.plans().list(status=ExecutionStatus.RUNNING.value, limit=limit)
        return [_plan_to_dict(p) for p in plans]

    def get_recent_executions(self, hours: int = 24, limit: int = 50) -> List[Dict[str, Any]]:
        """Return plans that started or completed in the last N hours."""
        since = utc_now() - timedelta(hours=hours)
        plans = self.uow.plans().list(limit=1000)
        recent = []
        for p in plans:
            started = p.started_at
            completed = p.completed_at
            if started and started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            if completed and completed.tzinfo is None:
                completed = completed.replace(tzinfo=timezone.utc)
            if (started and started >= since) or (completed and completed >= since):
                recent.append(p)
        recent.sort(key=lambda p: p.created_at, reverse=True)
        return [_plan_to_dict(p) for p in recent[:limit]]

    def get_execution(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Return a single execution plan with steps, history, and audit."""
        plan = self.uow.plans().get(plan_id)
        if plan is None:
            return None
        result = _plan_to_dict(plan)
        result["steps"] = [
            {
                "id": s.id,
                "step_number": s.step_number,
                "action": s.action,
                "status": s.status,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                "result": s.result,
                "error": s.error,
                "rollback_supported": s.rollback_supported,
            }
            for s in plan.steps
        ]
        result["history"] = [
            {
                "id": h.id,
                "old_status": h.old_status,
                "new_status": h.new_status,
                "changed_at": h.changed_at.isoformat() if h.changed_at else None,
                "changed_by": h.changed_by,
                "notes": h.notes,
            }
            for h in self.uow.history().list_for_plan(plan_id)
        ]
        result["audit"] = [
            {
                "id": a.id,
                "event": a.event,
                "timestamp": a.timestamp.isoformat() if a.timestamp else None,
                "actor": a.actor,
                "details": a.details,
            }
            for a in self.uow.audit().list_for_plan(plan_id)
        ]
        return result

    def get_execution_summary(self) -> Dict[str, Any]:
        """Return aggregate counts by status."""
        plans = self.uow.plans().list(limit=1000)
        by_status: Dict[str, int] = {}
        for p in plans:
            by_status[p.status] = by_status.get(p.status, 0) + 1
        return {
            "counts_by_status": by_status,
            "total": len(plans),
            "generated_at": utc_now().isoformat(),
        }


def _plan_to_dict(plan: ExecutionPlan) -> Dict[str, Any]:
    return {
        "id": plan.id,
        "decision_id": plan.decision_id,
        "action_type": plan.action_type,
        "status": plan.status,
        "checksum": plan.checksum,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "started_at": plan.started_at.isoformat() if plan.started_at else None,
        "completed_at": plan.completed_at.isoformat() if plan.completed_at else None,
        "expires_at": plan.expires_at.isoformat() if plan.expires_at else None,
        "payload": plan.payload,
    }


def get_execution_queue(uow: ExecutionUnitOfWork, limit: int = 50) -> List[Dict[str, Any]]:
    return ExecutionDashboard(uow).get_execution_queue(limit=limit)


def get_running(uow: ExecutionUnitOfWork, limit: int = 50) -> List[Dict[str, Any]]:
    return ExecutionDashboard(uow).get_running(limit=limit)


def get_recent_executions(uow: ExecutionUnitOfWork, hours: int = 24, limit: int = 50) -> List[Dict[str, Any]]:
    return ExecutionDashboard(uow).get_recent_executions(hours=hours, limit=limit)


def get_execution(uow: ExecutionUnitOfWork, plan_id: str) -> Optional[Dict[str, Any]]:
    return ExecutionDashboard(uow).get_execution(plan_id)


def get_execution_summary(uow: ExecutionUnitOfWork) -> Dict[str, Any]:
    return ExecutionDashboard(uow).get_execution_summary()
