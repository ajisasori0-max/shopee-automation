"""SQLAlchemy implementations of Event Bus repositories."""

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from commerceos.events.constants import EventStatus, WorkflowJobStatus
from commerceos.events.models import (
    DeadLetterEvent,
    DistributedLock,
    Event,
    EventSubscription,
    WorkflowHistory,
    WorkflowJob,
)
from commerceos.shared.value_objects.primitives import utc_now
from commerceos.events.repositories import (
    DeadLetterRepository,
    DistributedLockRepository,
    EventRepository,
    EventsUnitOfWork,
    EventSubscriptionRepository,
    WorkflowJobRepository,
)


class SQLAlchemyEventRepository(EventRepository):
    def __init__(self, session: Session):
        self.session = session

    def save(self, event: Event) -> Event:
        self.session.add(event)
        self.session.flush()
        return event

    def get(self, event_id: str) -> Optional[Event]:
        return self.session.query(Event).filter_by(id=event_id).first()

    def list(
        self,
        event_type: Optional[str] = None,
        status: Optional[str] = None,
        aggregate_type: Optional[str] = None,
        aggregate_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Event]:
        query = self.session.query(Event).order_by(Event.created_at.desc())
        if event_type:
            query = query.filter_by(event_type=event_type)
        if status:
            query = query.filter_by(status=status)
        if aggregate_type:
            query = query.filter_by(aggregate_type=aggregate_type)
        if aggregate_id:
            query = query.filter_by(aggregate_id=aggregate_id)
        return query.limit(limit).all()

    def get_by_status(self, status: str, limit: int = 100) -> List[Event]:
        return (
            self.session.query(Event)
            .filter_by(status=status)
            .order_by(Event.created_at.asc())
            .limit(limit)
            .all()
        )


class SQLAlchemyEventSubscriptionRepository(EventSubscriptionRepository):
    def __init__(self, session: Session):
        self.session = session

    def save(self, subscription: EventSubscription) -> EventSubscription:
        self.session.add(subscription)
        self.session.flush()
        return subscription

    def list(self, event_type: Optional[str] = None, enabled_only: bool = True) -> List[EventSubscription]:
        query = self.session.query(EventSubscription)
        if enabled_only:
            query = query.filter_by(enabled=True)
        if event_type:
            query = query.filter_by(event_type=event_type)
        return query.order_by(EventSubscription.handler_name).all()

    def get(self, event_type: str, handler_name: str) -> Optional[EventSubscription]:
        return self.session.query(EventSubscription).filter_by(event_type=event_type, handler_name=handler_name).first()


class SQLAlchemyWorkflowJobRepository(WorkflowJobRepository):
    def __init__(self, session: Session):
        self.session = session

    def save(self, job: WorkflowJob) -> WorkflowJob:
        self.session.add(job)
        self.session.flush()
        return job

    def get(self, job_id: str) -> Optional[WorkflowJob]:
        return (
            self.session.query(WorkflowJob)
            .options(joinedload(WorkflowJob.history))
            .filter_by(id=job_id)
            .first()
        )

    def list(
        self,
        status: Optional[str] = None,
        workflow_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[WorkflowJob]:
        query = self.session.query(WorkflowJob).order_by(WorkflowJob.created_at.desc())
        if status:
            query = query.filter_by(status=status)
        if workflow_name:
            query = query.filter_by(workflow_name=workflow_name)
        return query.limit(limit).all()

    def get_pending(self, limit: int = 100) -> List[WorkflowJob]:
        return (
            self.session.query(WorkflowJob)
            .filter_by(status=WorkflowJobStatus.QUEUED.value)
            .order_by(WorkflowJob.priority.desc(), WorkflowJob.scheduled_at.asc())
            .limit(limit)
            .all()
        )

    def record_history(self, entry: WorkflowHistory) -> WorkflowHistory:
        self.session.add(entry)
        self.session.flush()
        return entry

    def get_history(self, job_id: str) -> List[WorkflowHistory]:
        return (
            self.session.query(WorkflowHistory)
            .filter_by(job_id=job_id)
            .order_by(WorkflowHistory.changed_at.desc())
            .all()
        )


class SQLAlchemyDeadLetterRepository(DeadLetterRepository):
    def __init__(self, session: Session):
        self.session = session

    def save(self, entry: DeadLetterEvent) -> DeadLetterEvent:
        self.session.add(entry)
        self.session.flush()
        return entry

    def list(self, limit: int = 100) -> List[DeadLetterEvent]:
        return (
            self.session.query(DeadLetterEvent)
            .order_by(DeadLetterEvent.failed_at.desc())
            .limit(limit)
            .all()
        )

    def get_by_event(self, event_id: str) -> Optional[DeadLetterEvent]:
        return self.session.query(DeadLetterEvent).filter_by(event_id=event_id).first()


class SQLAlchemyDistributedLockRepository(DistributedLockRepository):
    def __init__(self, session: Session):
        self.session = session

    def acquire(self, lock: DistributedLock) -> bool:
        now = utc_now()
        existing = self.session.query(DistributedLock).filter_by(lock_name=lock.lock_name).first()
        if existing is None:
            self.session.add(lock)
            self.session.flush()
            return True
        expires = existing.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < now:
            # Expired lock: replace owner
            existing.owner_id = lock.owner_id
            existing.acquired_at = lock.acquired_at if lock.acquired_at else now
            existing.expires_at = lock.expires_at
            existing.job_id = lock.job_id
            self.session.flush()
            return True
        return False

    def release(self, lock_name: str, owner_id: str) -> bool:
        existing = self.session.query(DistributedLock).filter_by(lock_name=lock_name).first()
        if existing is None:
            return False
        if existing.owner_id != owner_id:
            return False
        self.session.delete(existing)
        self.session.flush()
        return True

    def get(self, lock_name: str) -> Optional[DistributedLock]:
        return self.session.query(DistributedLock).filter_by(lock_name=lock_name).first()

    def list_expired(self, before: datetime, limit: int = 100) -> List[DistributedLock]:
        return (
            self.session.query(DistributedLock)
            .filter(DistributedLock.expires_at < before)
            .limit(limit)
            .all()
        )


class SQLAlchemyEventsUnitOfWork(EventsUnitOfWork):
    def __init__(self, session: Session):
        self.session = session
        self._events = SQLAlchemyEventRepository(session)
        self._subscriptions = SQLAlchemyEventSubscriptionRepository(session)
        self._workflows = SQLAlchemyWorkflowJobRepository(session)
        self._dead_letters = SQLAlchemyDeadLetterRepository(session)
        self._locks = SQLAlchemyDistributedLockRepository(session)

    def __enter__(self) -> "SQLAlchemyEventsUnitOfWork":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()

    def events(self) -> EventRepository:
        return self._events

    def subscriptions(self) -> EventSubscriptionRepository:
        return self._subscriptions

    def workflows(self) -> WorkflowJobRepository:
        return self._workflows

    def dead_letters(self) -> DeadLetterRepository:
        return self._dead_letters

    def locks(self) -> DistributedLockRepository:
        return self._locks

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()


@contextmanager
def sqlalchemy_events_uow(session: Session):
    uow = SQLAlchemyEventsUnitOfWork(session)
    try:
        yield uow
        uow.commit()
    except Exception:
        uow.rollback()
        raise
