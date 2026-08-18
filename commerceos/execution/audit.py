"""Execution Engine audit logger.

Every event is recorded before, during, and after execution.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from commerceos.execution.constants import AuditEvent
from commerceos.execution.models import ExecutionAudit
from commerceos.execution.repositories import ExecutionUnitOfWork


class ExecutionAuditLogger:
    """Records fine-grained execution audit events."""

    def __init__(self, uow: ExecutionUnitOfWork):
        self.uow = uow

    def log(
        self,
        plan_id: str,
        event: AuditEvent,
        actor: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> ExecutionAudit:
        with self.uow:
            entry = ExecutionAudit(
                plan_id=plan_id,
                event=event.value,
                actor=actor,
                details=details or {},
            )
            self.uow.audit().record(entry)
            return entry

    def requested(self, plan_id: str, actor: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> ExecutionAudit:
        return self.log(plan_id, AuditEvent.REQUESTED, actor, details)

    def validated(self, plan_id: str, actor: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> ExecutionAudit:
        return self.log(plan_id, AuditEvent.VALIDATED, actor, details)

    def started(self, plan_id: str, actor: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> ExecutionAudit:
        return self.log(plan_id, AuditEvent.STARTED, actor, details)

    def step_completed(self, plan_id: str, step_number: int, result: Dict[str, Any], actor: Optional[str] = None) -> ExecutionAudit:
        return self.log(plan_id, AuditEvent.STEP_COMPLETED, actor, {"step_number": step_number, "result": result})

    def step_failed(self, plan_id: str, step_number: int, error: str, actor: Optional[str] = None) -> ExecutionAudit:
        return self.log(plan_id, AuditEvent.STEP_FAILED, actor, {"step_number": step_number, "error": error})

    def retry(self, plan_id: str, attempt: int, actor: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> ExecutionAudit:
        details = details or {}
        details["attempt"] = attempt
        return self.log(plan_id, AuditEvent.RETRY, actor, details)

    def rollback(self, plan_id: str, actor: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> ExecutionAudit:
        return self.log(plan_id, AuditEvent.ROLLBACK, actor, details)

    def finished(self, plan_id: str, status: str, actor: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> ExecutionAudit:
        details = details or {}
        details["final_status"] = status
        return self.log(plan_id, AuditEvent.FINISHED, actor, details)

    def cancelled(self, plan_id: str, actor: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> ExecutionAudit:
        return self.log(plan_id, AuditEvent.CANCELLED, actor, details)

    def expired(self, plan_id: str, actor: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> ExecutionAudit:
        return self.log(plan_id, AuditEvent.EXPIRED, actor, details)
