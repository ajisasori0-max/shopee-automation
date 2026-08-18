"""Retry manager for events and workflow jobs."""

from typing import Optional


class RetryManager:
    """Deterministic retry with exponential backoff and max attempts."""

    def __init__(self, max_attempts: int = 3, base_backoff_seconds: float = 2.0):
        self.max_attempts = max_attempts
        self.base_backoff_seconds = base_backoff_seconds

    def backoff_seconds(self, attempt: int) -> float:
        return self.base_backoff_seconds * (2 ** (attempt - 1))

    def should_retry(self, attempt_count: int, error_code: Optional[str]) -> bool:
        from commerceos.events.constants import is_retryable_error
        return attempt_count < self.max_attempts and is_retryable_error(error_code or "temporary")
