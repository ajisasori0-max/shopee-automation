"""Event Bus dashboard read API.

Stable interface for Streamlit and other dashboard consumers. No direct SQLAlchemy
model access.
"""
from commerceos.shared.value_objects.primitives import utc_now

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from commerceos.events.constants import EventStatus, WorkflowJobStatus
from commerceos.events.models import DeadLetterEvent, Event, WorkflowJob
from commerceos.events.repositories import EventsUnitOfWork


class EventsDashboard:
    """Stable read-only dashboard API for the Event Bus."""

    def __init__(self, uow: EventsUnitOfWork):
        self.uow = uow

    def get_recent_events(self, hours: int = 24, event_type: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        since = utc_now() - timedelta(hours=hours)
        events = self.uow.events().list(event_type=event_type, limit=1000)
        recent = []
        for e in events:
            created = e.created_at
            if created and created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if created and created >= since:
                recent.append(e)
        recent.sort(key=lambda e: e.created_at, reverse=True)
        return [_event_to_dict(e) for e in recent[:limit]]

    def get_failed_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        events = self.uow.events().list(status=EventStatus.FAILED.value, limit=limit)
        return [_event_to_dict(e) for e in events]

    def get_dead_letters(self, limit: int = 50) -> List[Dict[str, Any]]:
        entries = self.uow.dead_letters().list(limit=limit)
        return [_dead_letter_to_dict(e) for e in entries]

    def get_running_workflows(self, limit: int = 50) -> List[Dict[str, Any]]:
        jobs = self.uow.workflows().list(status=WorkflowJobStatus.RUNNING.value, limit=limit)
        return [_workflow_job_to_dict(j) for j in jobs]

    def get_workflow(self, job_id: str) -> Optional[Dict[str, Any]]:
        job = self.uow.workflows().get(job_id)
        if job is None:
            return None
        result = _workflow_job_to_dict(job)
        history = self.uow.workflows().get_history(job_id)
        result["history"] = [
            {
                "id": h.id,
                "old_status": h.old_status,
                "new_status": h.new_status,
                "changed_at": h.changed_at.isoformat() if h.changed_at else None,
                "notes": h.notes,
            }
            for h in history
        ]
        return result

    def get_event_summary(self) -> Dict[str, Any]:
        events = self.uow.events().list(limit=1000)
        by_status: Dict[str, int] = {}
        by_type: Dict[str, int] = {}
        for e in events:
            by_status[e.status] = by_status.get(e.status, 0) + 1
            by_type[e.event_type] = by_type.get(e.event_type, 0) + 1
        workflows = self.uow.workflows().list(limit=1000)
        workflow_by_status: Dict[str, int] = {}
        for w in workflows:
            workflow_by_status[w.status] = workflow_by_status.get(w.status, 0) + 1
        dead_letters = self.uow.dead_letters().list(limit=1000)
        return {
            "events": {"total": len(events), "by_status": by_status, "by_type": by_type},
            "workflows": {"total": len(workflows), "by_status": workflow_by_status},
            "dead_letters": len(dead_letters),
            "generated_at": utc_now().isoformat(),
        }


def _event_to_dict(event: Event) -> Dict[str, Any]:
    return {
        "id": event.id,
        "event_type": event.event_type,
        "aggregate_type": event.aggregate_type,
        "aggregate_id": event.aggregate_id,
        "payload": event.payload,
        "status": event.status,
        "attempt_count": event.attempt_count,
        "published_at": event.published_at.isoformat() if event.published_at else None,
        "processed_at": event.processed_at.isoformat() if event.processed_at else None,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


def _dead_letter_to_dict(entry: DeadLetterEvent) -> Dict[str, Any]:
    return {
        "id": entry.id,
        "event_id": entry.event_id,
        "reason": entry.reason,
        "failed_at": entry.failed_at.isoformat() if entry.failed_at else None,
        "retry_allowed": entry.retry_allowed,
        "metadata": entry.metadata_,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }


def _workflow_job_to_dict(job: WorkflowJob) -> Dict[str, Any]:
    return {
        "id": job.id,
        "workflow_name": job.workflow_name,
        "status": job.status,
        "priority": job.priority,
        "retry_count": job.retry_count,
        "payload": job.payload,
        "trigger_event_id": job.trigger_event_id,
        "scheduled_at": job.scheduled_at.isoformat() if job.scheduled_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }


def get_recent_events(uow: EventsUnitOfWork, hours: int = 24, event_type: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    return EventsDashboard(uow).get_recent_events(hours=hours, event_type=event_type, limit=limit)


def get_failed_events(uow: EventsUnitOfWork, limit: int = 50) -> List[Dict[str, Any]]:
    return EventsDashboard(uow).get_failed_events(limit=limit)


def get_dead_letters(uow: EventsUnitOfWork, limit: int = 50) -> List[Dict[str, Any]]:
    return EventsDashboard(uow).get_dead_letters(limit=limit)


def get_running_workflows(uow: EventsUnitOfWork, limit: int = 50) -> List[Dict[str, Any]]:
    return EventsDashboard(uow).get_running_workflows(limit=limit)


def get_workflow(uow: EventsUnitOfWork, job_id: str) -> Optional[Dict[str, Any]]:
    return EventsDashboard(uow).get_workflow(job_id)


def get_event_summary(uow: EventsUnitOfWork) -> Dict[str, Any]:
    return EventsDashboard(uow).get_event_summary()
