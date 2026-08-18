from commerceos.shared.value_objects.primitives import utc_now
"""Freshness evaluation helpers.

All time comparisons are done in UTC. Inputs may be naive or aware; naive values
are treated as UTC to be tolerant of SQLite storage.
"""

from datetime import datetime, timezone
from typing import Optional


def ensure_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def hours_since(value: Optional[datetime], now: Optional[datetime] = None) -> Optional[float]:
    value = ensure_utc(value)
    if value is None:
        return None
    now = ensure_utc(now) or utc_now()
    return (now - value).total_seconds() / 3600.0


def is_fresh(value: Optional[datetime], threshold_hours: float, now: Optional[datetime] = None) -> bool:
    h = hours_since(value, now)
    if h is None:
        return False
    return h < threshold_hours
