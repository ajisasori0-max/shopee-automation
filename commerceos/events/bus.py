"""Event Bus: publish, subscribe, dispatch.

Synchronous today. PostgreSQL-compatible. No business logic.
"""
from commerceos.shared.value_objects.primitives import utc_now

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from commerceos.events.constants import EventStatus, EventType
from commerceos.events.models import Event, EventSubscription
from commerceos.events.registry import HandlerRegistry
from commerceos.events.repositories import EventsUnitOfWork
from commerceos.events.sqlalchemy_repositories import SQLAlchemyEventsUnitOfWork


class EventBus:
    """Publish and dispatch domain events synchronously."""

    def __init__(
        self,
        session: Session,
        uow: Optional[EventsUnitOfWork] = None,
        registry: Optional[HandlerRegistry] = None,
    ):
        self.session = session
        self.uow = uow or SQLAlchemyEventsUnitOfWork(session)
        self.registry = registry or HandlerRegistry()

    def publish(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Event:
        """Persist and dispatch an event to all registered handlers."""
        event = Event(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
            status=EventStatus.CREATED.value,
            metadata_=metadata or {},
        )
        with self.uow:
            self.uow.events().save(event)

        event.status = EventStatus.PUBLISHED.value
        event.published_at = utc_now()
        with self.uow:
            self.uow.events().save(event)

        self._dispatch(event)
        return event

    def _dispatch(self, event: Event) -> None:
        handlers = self.registry.handlers_for(event.event_type)
        subscriptions = self.uow.subscriptions().list(event_type=event.event_type)
        registered_names = {s.handler_name for s in subscriptions}

        for handler in handlers:
            handler_name = getattr(handler, "__name__", str(handler))
            if handler_name not in registered_names:
                # Auto-subscribe on first dispatch if not persisted
                self.subscribe(event.event_type, handler_name)
                registered_names.add(handler_name)
            self._run_handler(event, handler)

        if not handlers and not subscriptions:
            event.status = EventStatus.PROCESSED.value
            event.processed_at = utc_now()
            with self.uow:
                self.uow.events().save(event)

    def _run_handler(self, event: Event, handler: Callable) -> None:
        event.status = EventStatus.PROCESSING.value
        event.attempt_count += 1
        with self.uow:
            self.uow.events().save(event)

        try:
            handler(event)
            event.status = EventStatus.PROCESSED.value
            event.processed_at = utc_now()
        except Exception as exc:
            event.status = EventStatus.FAILED.value
            event.metadata_["last_error"] = str(exc)

        with self.uow:
            self.uow.events().save(event)

    def subscribe(self, event_type: str, handler_name: str) -> EventSubscription:
        """Persist a subscription for an event type."""
        existing = self.uow.subscriptions().get(event_type, handler_name)
        if existing:
            return existing
        subscription = EventSubscription(event_type=event_type, handler_name=handler_name, enabled=True)
        with self.uow:
            self.uow.subscriptions().save(subscription)
        return subscription

    def unsubscribe(self, event_type: str, handler_name: str) -> bool:
        """Disable a persisted subscription."""
        existing = self.uow.subscriptions().get(event_type, handler_name)
        if existing is None:
            return False
        existing.enabled = False
        with self.uow:
            self.uow.subscriptions().save(existing)
        return True

    def register(self, event_type: str, handler: Callable) -> None:
        """Register an in-memory handler."""
        self.registry.register(event_type, handler)

    def dispatch(self, event_id: str) -> Optional[Event]:
        """Re-dispatch an existing event by ID."""
        event = self.uow.events().get(event_id)
        if event is None:
            return None
        self._dispatch(event)
        return event


def publish_event(
    session: Session,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    payload: Dict[str, Any],
) -> Event:
    """Convenience publish function."""
    return EventBus(session).publish(event_type, aggregate_type, aggregate_id, payload)
