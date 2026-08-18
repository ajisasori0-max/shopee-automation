"""Dead-letter queue for events that exceed retry limit."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from commerceos.events.constants import EventStatus
from commerceos.events.models import DeadLetterEvent, Event
from commerceos.events.sqlalchemy_repositories import SQLAlchemyEventsUnitOfWork
from commerceos.shared.value_objects.primitives import utc_now


class DeadLetterManager:
    """Moves failed events to dead_letter_events with reason preserved."""

    def __init__(self, session: Session, uow: Optional[SQLAlchemyEventsUnitOfWork] = None):
        self.session = session
        self.uow = uow or SQLAlchemyEventsUnitOfWork(session)

    def move(self, event: Event, reason: str, retry_allowed: bool = True) -> DeadLetterEvent:
        event.status = EventStatus.DEAD_LETTER.value
        event.processed_at = utc_now()
        with self.uow:
            self.uow.events().save(event)
            entry = DeadLetterEvent(
                event_id=event.id,
                reason=reason,
                retry_allowed=retry_allowed,
                metadata_={"event_type": event.event_type, "payload": event.payload},
            )
            self.uow.dead_letters().save(entry)
        return entry

    def retry(self, event_id: str) -> Optional[Event]:
        """Move a dead-letter event back to FAILED status for reprocessing."""
        with self.uow:
            event = self.uow.events().get(event_id)
            if event is None or event.status != EventStatus.DEAD_LETTER.value:
                return None
            event.status = EventStatus.FAILED.value
            event.attempt_count = 0
            self.uow.events().save(event)
            dl = self.uow.dead_letters().get_by_event(event_id)
            if dl:
                dl.retry_allowed = False
                # In a real DB with delete support, delete here; SQLite also works.
                self.session.delete(dl)
        return event
