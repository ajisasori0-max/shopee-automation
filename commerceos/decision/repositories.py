"""Decision Engine repository interfaces."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

from commerceos.decision.models import Decision, DecisionEvidence, DecisionHistory


class DecisionRepository(ABC):
    """Persist and retrieve proposed decisions."""

    @abstractmethod
    def save(self, decision: Decision) -> Decision:
        raise NotImplementedError

    @abstractmethod
    def save_many(self, decisions: List[Decision]) -> List[Decision]:
        raise NotImplementedError

    @abstractmethod
    def get(self, decision_id: str) -> Optional[Decision]:
        raise NotImplementedError

    @abstractmethod
    def list(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100,
    ) -> List[Decision]:
        raise NotImplementedError

    @abstractmethod
    def get_open(self, category: Optional[str] = None, limit: int = 100) -> List[Decision]:
        raise NotImplementedError

    @abstractmethod
    def get_history(self, decision_id: str) -> List[DecisionHistory]:
        raise NotImplementedError


class DecisionEvidenceRepository(ABC):
    """Persist and retrieve evidence linked to decisions."""

    @abstractmethod
    def save(self, evidence: DecisionEvidence) -> DecisionEvidence:
        raise NotImplementedError

    @abstractmethod
    def save_many(self, evidence: List[DecisionEvidence]) -> List[DecisionEvidence]:
        raise NotImplementedError

    @abstractmethod
    def list_for_decision(self, decision_id: str) -> List[DecisionEvidence]:
        raise NotImplementedError


class DecisionHistoryRepository(ABC):
    """Persist and retrieve decision history."""

    @abstractmethod
    def record(self, entry: DecisionHistory) -> DecisionHistory:
        raise NotImplementedError

    @abstractmethod
    def list_for_decision(self, decision_id: str) -> List[DecisionHistory]:
        raise NotImplementedError


class DecisionUnitOfWork(ABC):
    """Boundary for atomic decision operations."""

    @abstractmethod
    def __enter__(self) -> "DecisionUnitOfWork":
        raise NotImplementedError

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        raise NotImplementedError

    @abstractmethod
    def decisions(self) -> DecisionRepository:
        raise NotImplementedError

    @abstractmethod
    def evidence(self) -> DecisionEvidenceRepository:
        raise NotImplementedError

    @abstractmethod
    def history(self) -> DecisionHistoryRepository:
        raise NotImplementedError

    @abstractmethod
    def commit(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def rollback(self) -> None:
        raise NotImplementedError
