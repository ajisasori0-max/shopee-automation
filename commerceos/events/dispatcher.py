"""Event dispatcher for scheduled/queued events.

Currently synchronous; designed so an async worker can call `process_pending_events`.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from commerceos.events.bus import EventBus
from commerceos.events.constants import EventStatus, is_retryable_error
from commerceos.events.dead_letter import DeadLetterManager
from commerceos.events.models import Event
from commerceos.events.retry import RetryManager
from commerceos.events.sqlalchemy_repositories import SQLAlchemyEventsUnitOfWork


class EventDispatcher:
    """Polls for pending events and dispatches them in order."""

    def __init__(
        self,
        session: Session,
        event_bus: Optional[EventBus] = None,
        retry: Optional[RetryManager] = None,
        dead_letter: Optional[DeadLetterManager] = None,
    ):
        self.session = session
        self.bus = event_bus or EventBus(session)
        self.retry = retry or RetryManager()
        self.dead_letter = dead_letter or DeadLetterManager(session)

    def process_pending_events(self, limit: int = 100) -> Dict[str, Any]:
        """Dispatch all events in CREATED or FAILED status."""
        results = {"processed": 0, "failed": 0, "dead_letter": 0}
        uow = SQLAlchemyEventsUnitOfWork(self.session)
        for status in (EventStatus.CREATED.value, EventStatus.FAILED.value):
            events = uow.events().get_by_status(status, limit=limit)
            for event in events:
                result = self._dispatch_with_retry(event)
                if result == "processed":
                    results["processed"] += 1
                elif result == "dead_letter":
                    results["dead_letter"] += 1
                else:
                    results["failed"] += 1
        return results

    def _dispatch_with_retry(self, event: Event) -> str:
        last_error = None
        for attempt in range(1, self.retry.max_attempts + 1):
            try:
                self.bus._dispatch(event)
                return "processed"
            except Exception as exc:
                last_error = exc
                event.attempt_count += 1
                error_code = getattr(exc, "error_code", "temporary")
                if not is_retryable_error(error_code):
                    break
        if last_error:
            self.dead_letter.move(event, reason=str(last_error))
            return "dead_letter"
        return "processed"
