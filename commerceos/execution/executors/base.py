"""Execution Engine executor base and concrete executors.

All executors implement:
- dry_run(): simulate expected API calls and changes
- execute(): perform the action (or simulate with a fake client)
- rollback(): undo the action if supported

No marketplace calls are made directly in the base classes. Each executor
accepts an optional adapter/callback for marketplace interaction.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional

from commerceos.execution.constants import ActionType, ExecutionResult


class Executor(ABC):
    action_type: ActionType

    @abstractmethod
    def dry_run(self, parameters: Dict[str, Any], target: Dict[str, Any]) -> ExecutionResult:
        raise NotImplementedError

    @abstractmethod
    def execute(
        self,
        parameters: Dict[str, Any],
        target: Dict[str, Any],
        marketplace_fn: Optional[Callable] = None,
    ) -> ExecutionResult:
        raise NotImplementedError

    @abstractmethod
    def rollback(
        self,
        parameters: Dict[str, Any],
        target: Dict[str, Any],
        marketplace_fn: Optional[Callable] = None,
    ) -> ExecutionResult:
        raise NotImplementedError


class AdvertisingExecutor(Executor):
    action_type = ActionType.PAUSE_CAMPAIGN

    def dry_run(self, parameters: Dict[str, Any], target: Dict[str, Any]) -> ExecutionResult:
        action = target.get("id", "unknown")
        status = parameters.get("target_status", "paused")
        return ExecutionResult(
            success=True,
            action_type=self.action_type.value,
            entity_id=action,
            message=f"DRY RUN: set campaign {action} status to {status}",
            rollback_supported=True,
            details={"api_call": "update_campaign_status", "parameters": parameters, "target": target},
        )

    def execute(
        self,
        parameters: Dict[str, Any],
        target: Dict[str, Any],
        marketplace_fn: Optional[Callable] = None,
    ) -> ExecutionResult:
        action = target.get("id", "unknown")
        status = parameters.get("target_status", "paused")
        if marketplace_fn is not None:
            result = marketplace_fn(action, status)
            if isinstance(result, dict) and not result.get("ok", True):
                return ExecutionResult(
                    success=False,
                    action_type=self.action_type.value,
                    entity_id=action,
                    message=result.get("error", "marketplace error"),
                    error_code=result.get("error_code", "unknown"),
                    rollback_supported=False,
                    details=result,
                )
        return ExecutionResult(
            success=True,
            action_type=self.action_type.value,
            entity_id=action,
            message=f"Campaign {action} status set to {status}",
            rollback_supported=True,
            details={"previous_status": "active", "new_status": status},
        )

    def rollback(
        self,
        parameters: Dict[str, Any],
        target: Dict[str, Any],
        marketplace_fn: Optional[Callable] = None,
    ) -> ExecutionResult:
        action = target.get("id", "unknown")
        previous_status = "active"  # Simplified assumption
        if marketplace_fn is not None:
            marketplace_fn(action, previous_status)
        return ExecutionResult(
            success=True,
            action_type=ActionType.RESUME_CAMPAIGN.value,
            entity_id=action,
            message=f"Campaign {action} restored to {previous_status}",
            rollback_supported=False,
            details={"restored_status": previous_status},
        )


class PricingExecutor(Executor):
    action_type = ActionType.UPDATE_PRICE

    def dry_run(self, parameters: Dict[str, Any], target: Dict[str, Any]) -> ExecutionResult:
        item_id = target.get("id", "unknown")
        change_pct = parameters.get("change_pct", 0)
        return ExecutionResult(
            success=True,
            action_type=self.action_type.value,
            entity_id=item_id,
            message=f"DRY RUN: change price for item {item_id} by {change_pct * 100:.0f}%",
            rollback_supported=True,
            details={"change_pct": change_pct},
        )

    def execute(
        self,
        parameters: Dict[str, Any],
        target: Dict[str, Any],
        marketplace_fn: Optional[Callable] = None,
    ) -> ExecutionResult:
        item_id = target.get("id", "unknown")
        change_pct = parameters.get("change_pct", 0)
        if marketplace_fn is not None:
            marketplace_fn(item_id, change_pct)
        return ExecutionResult(
            success=True,
            action_type=self.action_type.value,
            entity_id=item_id,
            message=f"Price for item {item_id} changed by {change_pct * 100:.0f}%",
            rollback_supported=True,
            details={"change_pct": change_pct},
        )

    def rollback(
        self,
        parameters: Dict[str, Any],
        target: Dict[str, Any],
        marketplace_fn: Optional[Callable] = None,
    ) -> ExecutionResult:
        item_id = target.get("id", "unknown")
        change_pct = -parameters.get("change_pct", 0)
        if marketplace_fn is not None:
            marketplace_fn(item_id, change_pct)
        return ExecutionResult(
            success=True,
            action_type=ActionType.UPDATE_PRICE.value,
            entity_id=item_id,
            message=f"Price for item {item_id} rolled back by {change_pct * 100:.0f}%",
            rollback_supported=False,
            details={"change_pct": change_pct},
        )


class InventoryExecutor(Executor):
    action_type = ActionType.UPDATE_STOCK

    def dry_run(self, parameters: Dict[str, Any], target: Dict[str, Any]) -> ExecutionResult:
        variant_id = target.get("id", "unknown")
        adjustment = parameters.get("adjustment", 0)
        return ExecutionResult(
            success=True,
            action_type=self.action_type.value,
            entity_id=variant_id,
            message=f"DRY RUN: adjust stock for variant {variant_id} by {adjustment}",
            rollback_supported=True,
            details={"adjustment": adjustment},
        )

    def execute(
        self,
        parameters: Dict[str, Any],
        target: Dict[str, Any],
        marketplace_fn: Optional[Callable] = None,
    ) -> ExecutionResult:
        variant_id = target.get("id", "unknown")
        adjustment = parameters.get("adjustment", 0)
        if marketplace_fn is not None:
            marketplace_fn(variant_id, adjustment)
        return ExecutionResult(
            success=True,
            action_type=self.action_type.value,
            entity_id=variant_id,
            message=f"Stock for variant {variant_id} adjusted by {adjustment}",
            rollback_supported=True,
            details={"adjustment": adjustment},
        )

    def rollback(
        self,
        parameters: Dict[str, Any],
        target: Dict[str, Any],
        marketplace_fn: Optional[Callable] = None,
    ) -> ExecutionResult:
        variant_id = target.get("id", "unknown")
        adjustment = -parameters.get("adjustment", 0)
        if marketplace_fn is not None:
            marketplace_fn(variant_id, adjustment)
        return ExecutionResult(
            success=True,
            action_type=ActionType.UPDATE_STOCK.value,
            entity_id=variant_id,
            message=f"Stock for variant {variant_id} rolled back by {adjustment}",
            rollback_supported=False,
            details={"adjustment": adjustment},
        )


class FinanceExecutor(Executor):
    action_type = ActionType.RECORD_MANUAL_ADJUSTMENT

    def dry_run(self, parameters: Dict[str, Any], target: Dict[str, Any]) -> ExecutionResult:
        return ExecutionResult(
            success=True,
            action_type=self.action_type.value,
            entity_id=target.get("id"),
            message="DRY RUN: record manual adjustment",
            rollback_supported=False,
            details={"parameters": parameters},
        )

    def execute(
        self,
        parameters: Dict[str, Any],
        target: Dict[str, Any],
        marketplace_fn: Optional[Callable] = None,
    ) -> ExecutionResult:
        return ExecutionResult(
            success=True,
            action_type=self.action_type.value,
            entity_id=target.get("id"),
            message="Manual adjustment recorded",
            rollback_supported=False,
            details={"parameters": parameters},
        )

    def rollback(
        self,
        parameters: Dict[str, Any],
        target: Dict[str, Any],
        marketplace_fn: Optional[Callable] = None,
    ) -> ExecutionResult:
        return ExecutionResult(
            success=False,
            action_type=self.action_type.value,
            entity_id=target.get("id"),
            message="Manual adjustment cannot be rolled back automatically",
            rollback_supported=False,
            details={"reason": "no_automatic_rollback"},
        )


EXECUTOR_REGISTRY: Dict[str, Executor] = {
    ActionType.PAUSE_CAMPAIGN.value: AdvertisingExecutor(),
    ActionType.RESUME_CAMPAIGN.value: AdvertisingExecutor(),
    ActionType.ADJUST_BUDGET.value: AdvertisingExecutor(),
    ActionType.UPDATE_PRICE.value: PricingExecutor(),
    ActionType.UPDATE_STOCK.value: InventoryExecutor(),
    ActionType.RECORD_MANUAL_ADJUSTMENT.value: FinanceExecutor(),
}


def get_executor(action_type: str) -> Optional[Executor]:
    return EXECUTOR_REGISTRY.get(action_type)
