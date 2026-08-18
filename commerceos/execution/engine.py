"""Execution Engine.

Orchestrates validation, planning, execution, retry, rollback, and audit.
Never generates recommendations, never approves decisions, never modifies plans.
"""
from commerceos.shared.value_objects.primitives import utc_now

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from commerceos.decision.models import Decision
from commerceos.decision.repositories import DecisionUnitOfWork
from commerceos.decision.sqlalchemy_repositories import SQLAlchemyDecisionUnitOfWork
from commerceos.execution.audit import ExecutionAuditLogger
from commerceos.execution.constants import (
    ActionType,
    AuditEvent,
    ExecutionResult,
    ExecutionStatus,
    ExecutionStepStatus,
    is_retryable_error,
)
from commerceos.execution.executors.base import get_executor
from commerceos.execution.models import ExecutionHistory, ExecutionPlan, ExecutionStep
from commerceos.execution.planner import ExecutionPlanner
from commerceos.execution.repositories import ExecutionUnitOfWork
from commerceos.execution.retry import RetryManager
from commerceos.execution.rollback import RollbackManager
from commerceos.execution.sqlalchemy_repositories import SQLAlchemyExecutionUnitOfWork
from commerceos.execution.validators import ExecutionValidator, ValidationResult


class ExecutionEngine:
    """Execute approved decisions via immutable plans."""

    def __init__(
        self,
        session: Session,
        execution_uow: Optional[ExecutionUnitOfWork] = None,
        decision_uow: Optional[DecisionUnitOfWork] = None,
    ):
        self.session = session
        self.execution_uow = execution_uow or SQLAlchemyExecutionUnitOfWork(session)
        self.decision_uow = decision_uow or SQLAlchemyDecisionUnitOfWork(session)
        self.planner = ExecutionPlanner()
        self.audit = ExecutionAuditLogger(self.execution_uow)
        self.retry = RetryManager()
        self.rollback = RollbackManager(self.execution_uow)

    def create_plan(self, decision_id: str, actor: Optional[str] = None) -> Optional[ExecutionPlan]:
        """Create an immutable ExecutionPlan from an approved decision."""
        with self.decision_uow:
            decision = self.decision_uow.decisions().get(decision_id)
        if decision is None:
            self.audit.log(
                "",
                AuditEvent.REQUESTED,
                actor=actor,
                details={"decision_id": decision_id, "error": "decision not found"},
            )
            return None

        plan = self.planner.plan(decision)
        with self.execution_uow:
            self.execution_uow.plans().save(plan)
            for step in plan.steps:
                self.execution_uow.steps().save(step)
            self.execution_uow.history().record(
                ExecutionHistory(plan_id=plan.id, old_status=None, new_status=plan.status, changed_by=actor)
            )

        self.audit.requested(plan.id, actor, {"decision_id": decision_id, "action_type": plan.action_type})
        return plan

    def dry_run(self, plan_id: str, actor: Optional[str] = None) -> Dict[str, Any]:
        """Simulate execution without making marketplace changes."""
        with self.execution_uow:
            plan = self.execution_uow.plans().get(plan_id)
        if plan is None:
            return {"success": False, "error": "plan not found"}

        executor = get_executor(plan.action_type)
        if executor is None:
            return {"success": False, "error": f"no executor for action_type={plan.action_type}"}

        target = plan.payload.get("target_entity", {})
        parameters = plan.payload.get("parameters", {})
        result = executor.dry_run(parameters, target)
        return {
            "success": result.success,
            "plan_id": plan_id,
            "action_type": plan.action_type,
            "dry_run": True,
            "result": result.to_dict(),
        }

    def execute(
        self,
        plan_id: str,
        actor: Optional[str] = None,
        marketplace_fn: Optional[Callable] = None,
        validator: Optional[ExecutionValidator] = None,
        skip_validation: bool = False,
    ) -> Dict[str, Any]:
        """Execute a plan after validation. Supports retry and rollback."""
        with self.execution_uow:
            plan = self.execution_uow.plans().get(plan_id)
        if plan is None:
            return {"success": False, "error": "plan not found"}

        self.audit.requested(plan.id, actor)

        if not skip_validation:
            with self.decision_uow:
                decision = self.decision_uow.decisions().get(plan.decision_id)
            if decision is None:
                return {"success": False, "error": "decision not found"}

            existing = self.execution_uow.plans().list(decision_id=plan.decision_id, limit=1000)
            validator = validator or ExecutionValidator()
            validation = validator.validate(decision, plan, existing_plans=existing)
            if not validation.ok:
                self.audit.log(plan.id, AuditEvent.VALIDATED, actor, validation.to_dict())
                plan.status = ExecutionStatus.FAILED.value
                with self.execution_uow:
                    self.execution_uow.plans().save(plan)
                    self.execution_uow.history().record(
                        ExecutionHistory(
                            plan_id=plan.id,
                            old_status=ExecutionStatus.PLANNED.value,
                            new_status=ExecutionStatus.FAILED.value,
                            changed_by=actor,
                            notes="validation failed",
                        )
                    )
                return {"success": False, "plan_id": plan.id, "errors": validation.errors}
            self.audit.validated(plan.id, actor, validation.to_dict())

        with self.execution_uow:
            plan.status = ExecutionStatus.RUNNING.value
            plan.started_at = utc_now()
            self.execution_uow.plans().save(plan)
            self.execution_uow.history().record(
                ExecutionHistory(
                    plan_id=plan.id,
                    old_status=ExecutionStatus.PLANNED.value,
                    new_status=ExecutionStatus.RUNNING.value,
                    changed_by=actor,
                )
            )
        self.audit.started(plan.id, actor)

        executor = get_executor(plan.action_type)
        if executor is None:
            return self._fail_plan(plan, actor, f"no executor for action_type={plan.action_type}")

        target = plan.payload.get("target_entity", {})
        parameters = plan.payload.get("parameters", {})

        step_results = []
        for step in plan.steps:
            if step.status == ExecutionStepStatus.SKIPPED.value:
                continue
            step.status = ExecutionStepStatus.RUNNING.value
            step.started_at = utc_now()
            with self.execution_uow:
                self.execution_uow.steps().save(step)

            try:
                if step.action == f"validate_{plan.action_type}":
                    result = executor.dry_run(parameters, target)
                elif step.action == "publish_result":
                    result = ExecutionResult(
                        success=True,
                        action_type=plan.action_type,
                        entity_id=target.get("id"),
                        message="Result published to monitoring and feedback loop",
                        details={"feedback": True},
                    )
                else:
                    result = self.retry.run(executor.execute, parameters, target, marketplace_fn)

                step.status = ExecutionStepStatus.SUCCEEDED.value if result.success else ExecutionStepStatus.FAILED.value
                step.completed_at = utc_now()
                step.result = result.to_dict()
                step.rollback_supported = result.rollback_supported
                step_results.append(result.to_dict())
                event = AuditEvent.STEP_COMPLETED if result.success else AuditEvent.STEP_FAILED
                if result.success:
                    self.audit.step_completed(plan.id, step.step_number, result.to_dict(), actor)
                else:
                    self.audit.step_failed(plan.id, step.step_number, result.message or result.error_code or "unknown", actor)

                with self.execution_uow:
                    self.execution_uow.steps().save(step)

                if not result.success:
                    break
            except Exception as exc:
                step.status = ExecutionStepStatus.FAILED.value
                step.completed_at = utc_now()
                step.error = str(exc)
                step_results.append({"success": False, "error": str(exc)})
                self.audit.step_failed(plan.id, step.step_number, str(exc), actor)
                with self.execution_uow:
                    self.execution_uow.steps().save(step)
                break

        all_succeeded = all(r.get("success") for r in step_results)
        any_failed = any(not r.get("success") for r in step_results)

        if all_succeeded:
            final_status = ExecutionStatus.SUCCEEDED.value
        elif any_failed:
            final_status = ExecutionStatus.FAILED.value
            # Rollback any succeeded steps that support rollback
            rollback_report = self.rollback.rollback(plan, actor=actor or "system")
            if rollback_report["success"]:
                final_status = ExecutionStatus.ROLLED_BACK.value
            else:
                final_status = ExecutionStatus.PARTIAL.value
        else:
            final_status = ExecutionStatus.PARTIAL.value

        plan.status = final_status
        plan.completed_at = utc_now()
        with self.execution_uow:
            self.execution_uow.plans().save(plan)
            self.execution_uow.history().record(
                ExecutionHistory(
                    plan_id=plan.id,
                    old_status=ExecutionStatus.RUNNING.value,
                    new_status=final_status,
                    changed_by=actor,
                    notes=f"steps: {len(step_results)}",
                )
            )
        self.audit.finished(plan.id, final_status, actor, {"step_results": step_results})

        return {
            "success": all_succeeded,
            "plan_id": plan.id,
            "status": final_status,
            "step_results": step_results,
        }

    def _fail_plan(self, plan: ExecutionPlan, actor: Optional[str], error: str) -> Dict[str, Any]:
        plan.status = ExecutionStatus.FAILED.value
        plan.completed_at = utc_now()
        with self.execution_uow:
            self.execution_uow.plans().save(plan)
            self.execution_uow.history().record(
                ExecutionHistory(
                    plan_id=plan.id,
                    old_status=ExecutionStatus.RUNNING.value,
                    new_status=ExecutionStatus.FAILED.value,
                    changed_by=actor,
                    notes=error,
                )
            )
        self.audit.finished(plan.id, ExecutionStatus.FAILED.value, actor, {"error": error})
        return {"success": False, "plan_id": plan.id, "error": error}


class ExecutionLifecycleService:
    """Service wrapper for explicit lifecycle operations."""

    def __init__(self, uow: ExecutionUnitOfWork):
        self.uow = uow
        self.audit = ExecutionAuditLogger(uow)

    def cancel(self, plan_id: str, actor: Optional[str] = None, notes: Optional[str] = None) -> Optional[ExecutionPlan]:
        with self.uow:
            plan = self.uow.plans().get(plan_id)
            if plan is None:
                return None
            if plan.status in {ExecutionStatus.RUNNING.value, ExecutionStatus.PLANNED.value, ExecutionStatus.READY.value}:
                old_status = plan.status
                plan.status = ExecutionStatus.CANCELLED.value
                self.uow.plans().save(plan)
                self.uow.history().record(
                    ExecutionHistory(
                        plan_id=plan.id,
                        old_status=old_status,
                        new_status=ExecutionStatus.CANCELLED.value,
                        changed_by=actor,
                        notes=notes,
                    )
                )
            self.audit.cancelled(plan.id, actor, {"notes": notes})
            return plan

    def expire(self, plan_id: str, actor: Optional[str] = None, notes: Optional[str] = None) -> Optional[ExecutionPlan]:
        with self.uow:
            plan = self.uow.plans().get(plan_id)
            if plan is None:
                return None
            if plan.status not in {s.value for s in [ExecutionStatus.SUCCEEDED, ExecutionStatus.FAILED, ExecutionStatus.ROLLED_BACK, ExecutionStatus.CANCELLED]}:
                old_status = plan.status
                plan.status = ExecutionStatus.EXPIRED.value
                self.uow.plans().save(plan)
                self.uow.history().record(
                    ExecutionHistory(
                        plan_id=plan.id,
                        old_status=old_status,
                        new_status=ExecutionStatus.EXPIRED.value,
                        changed_by=actor,
                        notes=notes,
                    )
                )
            self.audit.expired(plan.id, actor, {"notes": notes})
            return plan
