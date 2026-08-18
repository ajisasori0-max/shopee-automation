"""Execution Engine retry manager.

Retries only transient failures. Never retries auth, validation, bad requests,
or duplicates.
"""

import time
from typing import Any, Callable, Dict, Optional

from commerceos.execution.constants import ExecutionResult, is_retryable_error


class RetryManager:
    """Deterministic retry logic for executor calls."""

    def __init__(self, max_attempts: int = 3, backoff_seconds: float = 5.0):
        self.max_attempts = max_attempts
        self.backoff_seconds = backoff_seconds

    def run(
        self,
        fn: Callable[..., ExecutionResult],
        parameters: dict,
        target: dict,
        marketplace_fn: Optional[Callable] = None,
    ) -> ExecutionResult:
        last_result: Optional[ExecutionResult] = None
        for attempt in range(1, self.max_attempts + 1):
            last_result = fn(parameters, target, marketplace_fn)
            if last_result.success:
                return last_result
            if not is_retryable_error(last_result.error_code):
                return last_result
            if attempt < self.max_attempts:
                time.sleep(self.backoff_seconds * (2 ** (attempt - 1)))
        return last_result or ExecutionResult(success=False, action_type="retry", message="no result")


def can_retry(result: ExecutionResult) -> bool:
    return is_retryable_error(result.error_code)
