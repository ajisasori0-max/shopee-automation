"""Execution Engine repository interfaces."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

from commerceos.execution.models import ExecutionPlan, ExecutionStep, ExecutionHistory, ExecutionAudit


class ExecutionPlanRepository(ABC):
    """Persist and retrieve execution plans."""

    @abstractmethod
    def save(self, plan: ExecutionPlan) -> ExecutionPlan:
        raise NotImplementedError

    @abstractmethod
    def get(self, plan_id: str) -> Optional[ExecutionPlan]:
        raise NotImplementedError

    @abstractmethod
    def list(
        self,
        status: Optional[str] = None,
        decision_id: Optional[str] = None,
        action_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[ExecutionPlan]:
        raise NotImplementedError

    @abstractmethod
    def get_by_decision(self, decision_id: str) -> Optional[ExecutionPlan]:
        raise NotImplementedError


class ExecutionStepRepository(ABC):
    """Persist and retrieve execution steps."""

    @abstractmethod
    def save(self, step: ExecutionStep) -> ExecutionStep:
        raise NotImplementedError

    @abstractmethod
    def save_many(self, steps: List[ExecutionStep]) -> List[ExecutionStep]:
        raise NotImplementedError

    @abstractmethod
    def list_for_plan(self, plan_id: str) -> List[ExecutionStep]:
        raise NotImplementedError


class ExecutionHistoryRepository(ABC):
    """Persist and retrieve execution status history."""

    @abstractmethod
    def record(self, entry: ExecutionHistory) -> ExecutionHistory:
        raise NotImplementedError

    @abstractmethod
    def list_for_plan(self, plan_id: str) -> List[ExecutionHistory]:
        raise NotImplementedError


class ExecutionAuditRepository(ABC):
    """Persist and retrieve execution audit events."""

    @abstractmethod
    def record(self, entry: ExecutionAudit) -> ExecutionAudit:
        raise NotImplementedError

    @abstractmethod
    def list_for_plan(self, plan_id: str) -> List[ExecutionAudit]:
        raise NotImplementedError

    @abstractmethod
    def list_recent(self, limit: int = 100) -> List[ExecutionAudit]:
        raise NotImplementedError


class ExecutionUnitOfWork(ABC):
    """Boundary for atomic execution operations."""

    @abstractmethod
    def __enter__(self) -> "ExecutionUnitOfWork":
        raise NotImplementedError

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        raise NotImplementedError

    @abstractmethod
    def plans(self) -> ExecutionPlanRepository:
        raise NotImplementedError

    @abstractmethod
    def steps(self) -> ExecutionStepRepository:
        raise NotImplementedError

    @abstractmethod
    def history(self) -> ExecutionHistoryRepository:
        raise NotImplementedError

    @abstractmethod
    def audit(self) -> ExecutionAuditRepository:
        raise NotImplementedError

    @abstractmethod
    def commit(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def rollback(self) -> None:
        raise NotImplementedError
