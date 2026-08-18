"""Connector errors with deterministic classification.

Every connector error is classified by retryability and root cause. This lets the
Sync Engine decide whether to retry, skip, or surface the failure without
marketplace-specific logic.
"""

from typing import Optional

from commerceos.platform.exceptions import CommerceOSError


class ConnectorError(CommerceOSError):
    """Base exception for connector failures."""
    pass


class ConnectorAuthError(ConnectorError):
    """Authentication or authorization failure. Do not retry without human intervention."""
    pass


class ConnectorRateLimitError(ConnectorError):
    """Rate limit exceeded. Retry after waiting."""

    def __init__(self, message: str, retry_after_seconds: Optional[int] = None):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class ConnectorTransientError(ConnectorError):
    """Temporary failure (network, timeout, 5xx). Safe to retry with backoff."""
    pass


class ConnectorPermanentError(ConnectorError):
    """Permanent failure (bad request, invalid payload). Do not retry blindly."""
    pass


class ConnectorConfigurationError(ConnectorError):
    """Connector is misconfigured (missing credentials, invalid store id, etc.)."""
    pass
