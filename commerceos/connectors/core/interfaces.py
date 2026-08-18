"""Connector core interfaces.

Every marketplace connector implements the MarketplaceConnector contract. The
contract exposes business capabilities, not marketplace endpoints, and returns
standardized ConnectorResult objects.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from commerceos.platform.secrets.manager import SecretManager


class SyncMode(str, Enum):
    """Whether a connector call is a full refresh or incremental delta."""

    FULL = "full"
    INCREMENTAL = "incremental"


class ConnectorResult:
    """Standardized result returned by every connector operation.

    Attributes:
        success: True if the operation succeeded.
        data: The canonical or raw payload, depending on the operation.
        errors: List of error dictionaries with message and optional code.
        metadata: Sync metadata including mode, cursor, timestamps, connector version, and source info.
    """

    def __init__(
        self,
        success: bool,
        data: Any = None,
        errors: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.success = success
        self.data = data
        self.errors = errors or []
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "errors": self.errors,
            "metadata": self.metadata,
        }

    @classmethod
    def ok(
        cls,
        data: Any = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "ConnectorResult":
        return cls(success=True, data=data, metadata=metadata)

    @classmethod
    def failed(
        cls,
        message: str,
        error_code: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "ConnectorResult":
        error: Dict[str, Any] = {"message": message}
        if error_code:
            error["code"] = error_code
        return cls(success=False, errors=[error], metadata=metadata)

    @classmethod
    def from_exception(
        cls,
        exc: Exception,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "ConnectorResult":
        from commerceos.connectors.core.errors import (
            ConnectorAuthError,
            ConnectorRateLimitError,
            ConnectorTransientError,
            ConnectorPermanentError,
        )

        error: Dict[str, Any] = {"message": str(exc)}
        if isinstance(exc, ConnectorAuthError):
            error["code"] = "auth_error"
            error["retryable"] = False
        elif isinstance(exc, ConnectorRateLimitError):
            error["code"] = "rate_limit"
            error["retryable"] = True
            error["retry_after_seconds"] = exc.retry_after_seconds
        elif isinstance(exc, ConnectorTransientError):
            error["code"] = "transient_error"
            error["retryable"] = True
        elif isinstance(exc, ConnectorPermanentError):
            error["code"] = "permanent_error"
            error["retryable"] = False
        else:
            error["code"] = "connector_error"
            error["retryable"] = False
        return cls(success=False, errors=[error], metadata=metadata)


class ConnectorHealth:
    """Deterministic health information for a connector.

    This becomes the foundation for Platform Stabilization in Epic 2.
    """

    def __init__(
        self,
        authenticated: bool,
        api_available: bool = False,
        last_successful_sync: Optional[datetime] = None,
        last_failed_sync: Optional[datetime] = None,
        rate_limit_remaining: Optional[int] = None,
        rate_limit_reset_at: Optional[datetime] = None,
        token_expires_at: Optional[datetime] = None,
        data_freshness_seconds: Optional[int] = None,
        status: str = "unknown",
        errors: Optional[List[str]] = None,
    ):
        self.authenticated = authenticated
        self.api_available = api_available
        self.last_successful_sync = last_successful_sync
        self.last_failed_sync = last_failed_sync
        self.rate_limit_remaining = rate_limit_remaining
        self.rate_limit_reset_at = rate_limit_reset_at
        self.token_expires_at = token_expires_at
        self.data_freshness_seconds = data_freshness_seconds
        self.status = status
        self.errors = errors or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "authenticated": self.authenticated,
            "api_available": self.api_available,
            "last_successful_sync": self.last_successful_sync.isoformat() if self.last_successful_sync else None,
            "last_failed_sync": self.last_failed_sync.isoformat() if self.last_failed_sync else None,
            "rate_limit_remaining": self.rate_limit_remaining,
            "rate_limit_reset_at": self.rate_limit_reset_at.isoformat() if self.rate_limit_reset_at else None,
            "token_expires_at": self.token_expires_at.isoformat() if self.token_expires_at else None,
            "data_freshness_seconds": self.data_freshness_seconds,
            "status": self.status,
            "errors": self.errors,
        }


class ConnectorAuth(ABC):
    """Abstract interface for connector authentication.

    Concrete implementations retrieve credentials from the provider-agnostic SecretManager
    using a connector-specific namespace.
    """

    @abstractmethod
    def get_credentials(self) -> Dict[str, Any]:
        """Return the credentials needed by the connector."""
        raise NotImplementedError

    @abstractmethod
    def refresh(self) -> ConnectorResult:
        """Refresh credentials if supported (e.g., OAuth token refresh)."""
        raise NotImplementedError

    @property
    @abstractmethod
    def is_authenticated(self) -> bool:
        """Return True if credentials are present and valid."""
        raise NotImplementedError


class MarketplaceConnector(ABC):
    """Abstract interface for marketplace connectors.

    A connector is responsible for:
    - Fetching marketplace-specific data.
    - Preserving the raw marketplace payload.
    - Mapping raw payloads to canonical CommerceOS entities.
    - Returning standardized ConnectorResult objects.
    - Exposing deterministic health information.

    A connector does NOT write to the canonical database directly.
    That is the responsibility of the Ingestion bounded context / Sync Engine.
    """

    @property
    @abstractmethod
    def marketplace_code(self) -> str:
        """Return the marketplace code, e.g. 'shopee'."""
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the human-readable marketplace name."""
        raise NotImplementedError

    @property
    @abstractmethod
    def version(self) -> str:
        """Return the connector implementation version."""
        raise NotImplementedError

    @property
    @abstractmethod
    def auth(self) -> ConnectorAuth:
        """Return the connector's authentication object."""
        raise NotImplementedError

    @abstractmethod
    def health(self) -> ConnectorHealth:
        """Return deterministic health information for the connector."""
        raise NotImplementedError

    @abstractmethod
    def fetch_orders(
        self, sync_mode: SyncMode = SyncMode.INCREMENTAL, cursor: Optional[str] = None, **kwargs
    ) -> ConnectorResult:
        """Fetch orders. Returns standardized result with raw and canonical data."""
        raise NotImplementedError

    @abstractmethod
    def fetch_products(
        self, sync_mode: SyncMode = SyncMode.INCREMENTAL, cursor: Optional[str] = None, **kwargs
    ) -> ConnectorResult:
        """Fetch products. Returns standardized result with raw and canonical data."""
        raise NotImplementedError

    @abstractmethod
    def fetch_inventory(
        self, sync_mode: SyncMode = SyncMode.INCREMENTAL, cursor: Optional[str] = None, **kwargs
    ) -> ConnectorResult:
        """Fetch inventory. Returns standardized result with raw and canonical data."""
        raise NotImplementedError

    @abstractmethod
    def fetch_payments(
        self, sync_mode: SyncMode = SyncMode.INCREMENTAL, cursor: Optional[str] = None, **kwargs
    ) -> ConnectorResult:
        """Fetch payments. Returns standardized result with raw and canonical data."""
        raise NotImplementedError

    @abstractmethod
    def fetch_ads(
        self, sync_mode: SyncMode = SyncMode.INCREMENTAL, cursor: Optional[str] = None, **kwargs
    ) -> ConnectorResult:
        """Fetch advertising data. Returns standardized result with raw and canonical data."""
        raise NotImplementedError


class ConnectorRegistry:
    """Registry of available marketplace connectors."""

    def __init__(self):
        self._connectors: Dict[str, MarketplaceConnector] = {}

    def register(self, connector: MarketplaceConnector) -> None:
        self._connectors[connector.marketplace_code] = connector

    def get(self, marketplace_code: str) -> Optional[MarketplaceConnector]:
        return self._connectors.get(marketplace_code)

    def list(self) -> List[str]:
        return list(self._connectors.keys())

    def health(self, marketplace_code: str) -> Optional[ConnectorHealth]:
        connector = self.get(marketplace_code)
        if connector is None:
            return None
        return connector.health()

    def health_all(self) -> Dict[str, ConnectorHealth]:
        return {code: connector.health() for code, connector in self._connectors.items()}
