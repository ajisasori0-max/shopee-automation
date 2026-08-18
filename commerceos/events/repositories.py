"""Event Bus repository interfaces."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

from commerceos.events.models import Event, EventSubscription, WorkflowJob, WorkflowHistory, DeadLetterEvent, DistributedLock


class EventRepository(ABC):
    @abstractmethod
    def save(self, event: Event) -> Event:
        raise NotImplementedError

    @abstractmethod
    def get(self, event_id: str) -> Optional[Event]:
        raise NotImplementedError

    @abstractmethod
    def list(
        self,
        event_type: Optional[str] = None,
        status: Optional[str] = None,
        aggregate_type: Optional[str] = None,
        aggregate_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Event]:
        raise NotImplementedError

    @abstractmethod
    def get_by_status(self, status: str, limit: int = 100) -> List[Event]:
        raise NotImplementedError


class EventSubscriptionRepository(ABC):
    @abstractmethod
    def save(self, subscription: EventSubscription) -> EventSubscription:
        raise NotImplementedError

    @abstractmethod
    def list(self, event_type: Optional[str] = None, enabled_only: bool = True) -> List[EventSubscription]:
        raise NotImplementedError

    @abstractmethod
    def get(self, event_type: str, handler_name: str) -> Optional[EventSubscription]:
        raise NotImplementedError


class WorkflowJobRepository(ABC):
    @abstractmethod
    def save(self, job: WorkflowJob) -> WorkflowJob:
        raise NotImplementedError

    @abstractmethod
    def get(self, job_id: str) -> Optional[WorkflowJob]:
        raise NotImplementedError

    @abstractmethod
    def list(
        self,
        status: Optional[str] = None,
        workflow_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[WorkflowJob]:
        raise NotImplementedError

    @abstractmethod
    def get_pending(self, limit: int = 100) -> List[WorkflowJob]:
        raise NotImplementedError

    @abstractmethod
    def record_history(self, entry: WorkflowHistory) -> WorkflowHistory:
        raise NotImplementedError

    @abstractmethod
    def get_history(self, job_id: str) -> List[WorkflowHistory]:
        raise NotImplementedError


class DeadLetterRepository(ABC):
    @abstractmethod
    def save(self, entry: DeadLetterEvent) -> DeadLetterEvent:
        raise NotImplementedError

    @abstractmethod
    def list(self, limit: int = 100) -> List[DeadLetterEvent]:
        raise NotImplementedError

    @abstractmethod
    def get_by_event(self, event_id: str) -> Optional[DeadLetterEvent]:
        raise NotImplementedError


class DistributedLockRepository(ABC):
    @abstractmethod
    def acquire(self, lock: DistributedLock) -> bool:
        raise NotImplementedError

    @abstractmethod
    def release(self, lock_name: str, owner_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get(self, lock_name: str) -> Optional[DistributedLock]:
        raise NotImplementedError

    @abstractmethod
    def list_expired(self, before: datetime, limit: int = 100) -> List[DistributedLock]:
        raise NotImplementedError


class EventsUnitOfWork(ABC):
    @abstractmethod
    def __enter__(self) -> "EventsUnitOfWork":
        raise NotImplementedError

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        raise NotImplementedError

    @abstractmethod
    def events(self) -> EventRepository:
        raise NotImplementedError

    @abstractmethod
    def subscriptions(self) -> EventSubscriptionRepository:
        raise NotImplementedError

    @abstractmethod
    def workflows(self) -> WorkflowJobRepository:
        raise NotImplementedError

    @abstractmethod
    def dead_letters(self) -> DeadLetterRepository:
        raise NotImplementedError

    @abstractmethod
    def locks(self) -> DistributedLockRepository:
        raise NotImplementedError

    @abstractmethod
    def commit(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def rollback(self) -> None:
        raise NotImplementedError
