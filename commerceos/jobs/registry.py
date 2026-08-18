"""Job registry for deterministic automation runtime.

Defines standard operational jobs and their metadata. Jobs are simple callables
registered by name and group. The runner handles idempotency, history, and
failure recording.
"""
from __future__ import annotations


from dataclasses import dataclass
from typing import Callable, Dict, Optional


@dataclass(frozen=True)
class JobDefinition:
    """Metadata for one operational job."""

    name: str
    group: Optional[str] = None
    description: str = ""
    schedule_hint: str = ""  # e.g., "daily 08:00" — for docs only, not enforced here
    idempotency_key: Optional[Callable[[], str]] = None


class JobRegistry:
    """In-memory registry of job definitions."""

    def __init__(self):
        self._jobs: Dict[str, JobDefinition] = {}
        self._handlers: Dict[str, Callable] = {}

    def register(
        self,
        name: str,
        handler: Callable,
        group: Optional[str] = None,
        description: str = "",
        schedule_hint: str = "",
        idempotency_key: Optional[Callable[[], str]] = None,
    ) -> JobDefinition:
        """Register a job and its handler."""
        definition = JobDefinition(
            name=name,
            group=group,
            description=description,
            schedule_hint=schedule_hint,
            idempotency_key=idempotency_key,
        )
        self._jobs[name] = definition
        self._handlers[name] = handler
        return definition

    def get(self, name: str) -> Optional[JobDefinition]:
        return self._jobs.get(name)

    def get_handler(self, name: str) -> Optional[Callable]:
        return self._handlers.get(name)

    def list_jobs(self, group: Optional[str] = None) -> Dict[str, JobDefinition]:
        if group is None:
            return dict(self._jobs)
        return {name: d for name, d in self._jobs.items() if d.group == group}

    def names(self) -> list[str]:
        return list(self._jobs.keys())
