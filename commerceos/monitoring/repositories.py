"""Monitoring repository interfaces.

These abstract interfaces isolate the monitoring service from SQLAlchemy. Tests
and future PostgreSQL/S3 adapters can implement them without changing service
logic.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

from commerceos.monitoring.models import HealthCheck, Alert, HealthSnapshot


class HealthCheckRepository(ABC):
    """Persist and retrieve point-in-time health checks."""

    @abstractmethod
    def save(self, check: HealthCheck) -> HealthCheck:
        raise NotImplementedError

    @abstractmethod
    def save_many(self, checks: List[HealthCheck]) -> List[HealthCheck]:
        raise NotImplementedError

    @abstractmethod
    def list(
        self,
        component: Optional[str] = None,
        component_instance: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[HealthCheck]:
        raise NotImplementedError

    @abstractmethod
    def latest_by_component(
        self,
        component: Optional[str] = None,
        component_instance: Optional[str] = None,
    ) -> List[HealthCheck]:
        raise NotImplementedError


class AlertRepository(ABC):
    """Persist and retrieve operational alerts with deduplication support."""

    @abstractmethod
    def get_open(
        self,
        category: Optional[str] = None,
        component: Optional[str] = None,
        component_instance: Optional[str] = None,
    ) -> List[Alert]:
        raise NotImplementedError

    @abstractmethod
    def find_matching(
        self,
        category: str,
        component: str,
        component_instance: Optional[str] = None,
    ) -> Optional[Alert]:
        """Return an open alert matching the deduplication key."""
        raise NotImplementedError

    @abstractmethod
    def save(self, alert: Alert) -> Alert:
        raise NotImplementedError

    @abstractmethod
    def resolve(self, alert_id: str) -> Optional[Alert]:
        raise NotImplementedError

    @abstractmethod
    def list_recent(self, limit: int = 50, status: Optional[str] = None) -> List[Alert]:
        raise NotImplementedError


class HealthSnapshotRepository(ABC):
    """Persist and retrieve aggregated health snapshots."""

    @abstractmethod
    def save(self, snapshot: HealthSnapshot) -> HealthSnapshot:
        raise NotImplementedError

    @abstractmethod
    def latest(self) -> Optional[HealthSnapshot]:
        raise NotImplementedError

    @abstractmethod
    def list(self, limit: int = 50) -> List[HealthSnapshot]:
        raise NotImplementedError


class MonitoringUnitOfWork(ABC):
    """Boundary for atomic monitoring operations."""

    @abstractmethod
    def __enter__(self) -> "MonitoringUnitOfWork":
        raise NotImplementedError

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        raise NotImplementedError

    @abstractmethod
    def health_checks(self) -> HealthCheckRepository:
        raise NotImplementedError

    @abstractmethod
    def alerts(self) -> AlertRepository:
        raise NotImplementedError

    @abstractmethod
    def snapshots(self) -> HealthSnapshotRepository:
        raise NotImplementedError

    @abstractmethod
    def commit(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def rollback(self) -> None:
        raise NotImplementedError
