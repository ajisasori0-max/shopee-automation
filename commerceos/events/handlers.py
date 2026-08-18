"""Built-in event handlers.

Each handler is a pure function: receives an Event, performs side effects via the
existing services, and returns nothing. Handlers are idempotent where possible.
"""

from typing import Any, Callable, Dict

from commerceos.events.bus import EventBus
from commerceos.events.models import Event


Handler = Callable[[Event], None]


class Handlers:
    """Registry of built-in business handlers."""

    _handlers: Dict[str, Handler] = {}

    @classmethod
    def register(cls, name: str, handler: Handler) -> None:
        cls._handlers[name] = handler

    @classmethod
    def get(cls, name: str) -> Handler:
        return cls._handlers[name]

    @classmethod
    def all(cls) -> Dict[str, Handler]:
        return dict(cls._handlers)


def log_handler(event: Event) -> None:
    """Default handler: just logs event receipt in event metadata."""
    if event.metadata_ is None:
        event.metadata_ = {}
    event.metadata_["log_handler_seen"] = True


def refresh_kpis_handler(event: Event) -> None:
    """Stub handler: marks that KPI refresh should be requested."""
    event.metadata_["refresh_kpis_requested"] = True


def refresh_commerce_state_handler(event: Event) -> None:
    """Stub handler: marks that commerce state refresh should be requested."""
    event.metadata_["refresh_commerce_state_requested"] = True


def generate_monitoring_snapshot_handler(event: Event) -> None:
    """Stub handler: marks that monitoring snapshot should be requested."""
    event.metadata_["monitoring_snapshot_requested"] = True


def generate_intelligence_handler(event: Event) -> None:
    """Stub handler: marks that intelligence refresh should be requested."""
    event.metadata_["generate_intelligence_requested"] = True


def generate_decisions_handler(event: Event) -> None:
    """Stub handler: marks that decision generation should be requested."""
    event.metadata_["generate_decisions_requested"] = True


Handlers.register("log_handler", log_handler)
Handlers.register("refresh_kpis_handler", refresh_kpis_handler)
Handlers.register("refresh_commerce_state_handler", refresh_commerce_state_handler)
Handlers.register("generate_monitoring_snapshot_handler", generate_monitoring_snapshot_handler)
Handlers.register("generate_intelligence_handler", generate_intelligence_handler)
Handlers.register("generate_decisions_handler", generate_decisions_handler)
