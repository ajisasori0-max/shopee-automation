"""Execution Engine rollback manager.

Rolls back only when the step/executor supports rollback. Records success,
failure, and reason explicitly.
"""

from typing import Any, Dict, List

from commerceos.execution.constants import ExecutionResult, ExecutionStepStatus, ExecutionStatus
from commerceos.execution.executors.base import get_executor
from commerceos.execution.models import ExecutionPlan, ExecutionStep
from commerceos.execution.repositories import ExecutionUnitOfWork


class RollbackManager:
    """Deterministic rollback of failed execution plans."""

    def __init__(self, uow: ExecutionUnitOfWork):
        self.uow = uow

    def rollback(self, plan: ExecutionPlan, actor: str = "system") -> Dict[str, Any]:
        results = []
        succeeded = True
        # Roll back steps in reverse order, only those that succeeded and support rollback
        for step in reversed(plan.steps):
            if step.status != ExecutionStepStatus.SUCCEEDED.value:
                continue
            if not step.rollback_supported:
                results.append({
                    "step": step.step_number,
                    "action": step.action,
                    "rolled_back": False,
                    "reason": "rollback not supported for this step",
                })
                continue
            executor = get_executor(plan.action_type)
            if executor is None:
                results.append({
                    "step": step.step_number,
                    "action": step.action,
                    "rolled_back": False,
                    "reason": "no executor found",
                })
                succeeded = False
                continue
            try:
                target = plan.payload.get("target_entity", {})
                parameters = plan.payload.get("parameters", {})
                result = executor.rollback(parameters, target)
                step.status = ExecutionStepStatus.ROLLED_BACK.value
                step.result = result.to_dict()
                results.append({
                    "step": step.step_number,
                    "action": step.action,
                    "rolled_back": result.success,
                    "message": result.message,
                })
                if not result.success:
                    succeeded = False
            except Exception as exc:
                step.status = ExecutionStepStatus.FAILED.value
                step.error = str(exc)
                succeeded = False
                results.append({
                    "step": step.step_number,
                    "action": step.action,
                    "rolled_back": False,
                    "reason": str(exc),
                })

        with self.uow:
            plan.status = ExecutionStatus.ROLLED_BACK.value if succeeded else ExecutionStatus.PARTIAL.value
            self.uow.plans().save(plan)
            for step in plan.steps:
                self.uow.steps().save(step)

        return {"success": succeeded, "results": results}
