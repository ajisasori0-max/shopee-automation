"""Event Bus constants and enumerations."""

from enum import Enum


class EventStatus(str, Enum):
    CREATED = "created"
    PUBLISHED = "published"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class WorkflowJobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class EventType(str, Enum):
    ORDERS_SYNCED = "orders_synced"
    PAYMENTS_SYNCED = "payments_synced"
    PRODUCTS_SYNCED = "products_synced"
    INVENTORY_UPDATED = "inventory_updated"
    KPIS_REFRESHED = "kpis_refreshed"
    COMMERCE_STATE_UPDATED = "commerce_state_updated"
    HEALTH_SNAPSHOT_CREATED = "health_snapshot_created"
    INSIGHT_GENERATED = "insight_generated"
    DECISION_CREATED = "decision_created"
    DECISION_APPROVED = "decision_approved"
    EXECUTION_REQUESTED = "execution_requested"
    EXECUTION_STARTED = "execution_started"
    EXECUTION_SUCCEEDED = "execution_succeeded"
    EXECUTION_FAILED = "execution_failed"
    ROLLBACK_COMPLETED = "rollback_completed"


class Priority(int, Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


TRANSIENT_ERROR_CODES = {
    "timeout",
    "rate_limit",
    "network",
    "temporary",
    "unavailable",
    "lock_conflict",
}


NON_RETRYABLE_ERROR_CODES = {
    "validation",
    "auth",
    "authentication",
    "bad_request",
    "not_found",
    "forbidden",
    "duplicate",
}


def is_retryable_error(error_code: str) -> bool:
    if error_code in NON_RETRYABLE_ERROR_CODES:
        return False
    return error_code in TRANSIENT_ERROR_CODES


def is_terminal_event_status(status: EventStatus) -> bool:
    return status in {EventStatus.PROCESSED, EventStatus.DEAD_LETTER}
