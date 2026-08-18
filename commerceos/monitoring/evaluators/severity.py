"""Severity evaluation helpers for health checks."""

from datetime import datetime, timezone
from typing import Optional

from commerceos.monitoring.constants import Severity
from commerceos.monitoring.evaluators.freshness import hours_since


def severity_from_hours(
    value: Optional[datetime],
    critical_hours: float,
    warning_hours: float,
    now: Optional[datetime] = None,
) -> Severity:
    """Return severity based on how stale a timestamp is."""
    h = hours_since(value, now)
    if h is None:
        return Severity.CRITICAL
    if h >= critical_hours:
        return Severity.CRITICAL
    if h >= warning_hours:
        return Severity.WARNING
    return Severity.INFO


def severity_from_score(
    score: Optional[float],
    critical_threshold: float = 0.5,
    warning_threshold: float = 0.8,
) -> Severity:
    """Return severity based on a score where 1.0 is perfect."""
    if score is None:
        return Severity.WARNING
    if score < critical_threshold:
        return Severity.CRITICAL
    if score < warning_threshold:
        return Severity.WARNING
    return Severity.INFO


def severity_from_ratio(
    ratio: Optional[float],
    critical_threshold: float = 0.1,
    warning_threshold: float = 0.25,
) -> Severity:
    """Return severity based on a ratio where 1.0 is best (e.g. rate limit headroom)."""
    if ratio is None:
        return Severity.WARNING
    if ratio <= critical_threshold:
        return Severity.CRITICAL
    if ratio <= warning_threshold:
        return Severity.WARNING
    return Severity.INFO
