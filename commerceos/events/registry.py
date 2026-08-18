"""Handler registry for in-memory event subscriptions."""

from typing import Any, Callable, Dict, List


class HandlerRegistry:
    """Stores event handler callables in memory."""

    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}

    def register(self, event_type: str, handler: Callable) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def unregister(self, event_type: str, handler: Callable) -> None:
        if event_type in self._handlers:
            self._handlers[event_type] = [h for h in self._handlers[event_type] if h != handler]

    def handlers_for(self, event_type: str) -> List[Callable]:
        return list(self._handlers.get(event_type, []))

    def list_types(self) -> List[str]:
        return list(self._handlers.keys())
