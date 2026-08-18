"""Execution Engine constants and status helpers."""

from typing import Any, Dict, List, Optional, Set
from enum import Enum


class ExecutionStatus(str, Enum):
    PLANNED = "planned"
    READY = "ready"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PARTIAL = "partial"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ExecutionStepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    SKIPPED = "skipped"


class ActionType(str, Enum):
    PAUSE_CAMPAIGN = "pause_campaign"
    RESUME_CAMPAIGN = "resume_campaign"
    ADJUST_BUDGET = "adjust_budget"
    UPDATE_PRICE = "update_price"
    UPDATE_STOCK = "update_stock"
    RECORD_MANUAL_ADJUSTMENT = "record_manual_adjustment"


class AuditEvent(str, Enum):
    REQUESTED = "requested"
    VALIDATED = "validated"
    STARTED = "started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    RETRY = "retry"
    ROLLBACK = "rollback"
    FINISHED = "finished"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


RETRYABLE_STATUSES: Set[ExecutionStatus] = {
    ExecutionStatus.FAILED,
    ExecutionStatus.PARTIAL,
}

NON_RETRYABLE_ERROR_CODES: Set[str] = {
    "auth",
    "authentication",
    "validation",
    "bad_request",
    "duplicate",
    "forbidden",
    "not_found",
}

TRANSIENT_ERROR_CODES: Set[str] = {
    "timeout",
    "rate_limit",
    "temporary",
    "network",
    "server_error",
    "unavailable",
}


class ExecutionResult:
    """Lightweight result object returned by executors."""

    def __init__(
        self,
        success: bool,
        action_type: str,
        entity_id: Optional[str] = None,
        message: str = "",
        error_code: Optional[str] = None,
        details: Optional[dict] = None,
        rollback_supported: bool = False,
    ):
        self.success = success
        self.action_type = action_type
        self.entity_id = entity_id
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.rollback_supported = rollback_supported

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "action_type": self.action_type,
            "entity_id": self.entity_id,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details,
            "rollback_supported": self.rollback_supported,
        }

    @property
    def is_retryable(self) -> bool:
        if self.success:
            return False
        return self.error_code in TRANSIENT_ERROR_CODES


from typing import Optional


def is_retryable_error(error_code: Optional[str]) -> bool:
    if error_code is None:
        return True
    if error_code.lower() in NON_RETRYABLE_ERROR_CODES:
        return False
    return error_code.lower() in TRANSIENT_ERROR_CODES


def is_terminal_status(status: ExecutionStatus) -> bool:
    return status in {
        ExecutionStatus.SUCCEEDED,
        ExecutionStatus.FAILED,
        ExecutionStatus.ROLLED_BACK,
        ExecutionStatus.CANCELLED,
        ExecutionStatus.EXPIRED,
    }
