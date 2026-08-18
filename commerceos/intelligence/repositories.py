"""Intelligence repository interfaces."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

from commerceos.intelligence.models import Insight, TrendSnapshot


class InsightRepository(ABC):
    """Persist and retrieve business insights."""

    @abstractmethod
    def save(self, insight: Insight) -> Insight:
        raise NotImplementedError

    @abstractmethod
    def save_many(self, insights: List[Insight]) -> List[Insight]:
        raise NotImplementedError

    @abstractmethod
    def list(
        self,
        category: Optional[str] = None,
        severity: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Insight]:
        raise NotImplementedError

    @abstractmethod
    def latest_by_category(self, limit: int = 100) -> List[Insight]:
        raise NotImplementedError

    @abstractmethod
    def acknowledge(self, insight_id: str) -> Optional[Insight]:
        raise NotImplementedError


class TrendSnapshotRepository(ABC):
    """Persist and retrieve trend snapshots."""

    @abstractmethod
    def save(self, snapshot: TrendSnapshot) -> TrendSnapshot:
        raise NotImplementedError

    @abstractmethod
    def save_many(self, snapshots: List[TrendSnapshot]) -> List[TrendSnapshot]:
        raise NotImplementedError

    @abstractmethod
    def list(
        self,
        metric: Optional[str] = None,
        period: Optional[str] = None,
        limit: int = 100,
    ) -> List[TrendSnapshot]:
        raise NotImplementedError

    @abstractmethod
    def latest(self, metric: str, period: str) -> Optional[TrendSnapshot]:
        raise NotImplementedError


class IntelligenceUnitOfWork(ABC):
    """Boundary for atomic intelligence operations."""

    @abstractmethod
    def __enter__(self) -> "IntelligenceUnitOfWork":
        raise NotImplementedError

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        raise NotImplementedError

    @abstractmethod
    def insights(self) -> InsightRepository:
        raise NotImplementedError

    @abstractmethod
    def trends(self) -> TrendSnapshotRepository:
        raise NotImplementedError

    @abstractmethod
    def commit(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def rollback(self) -> None:
        raise NotImplementedError
