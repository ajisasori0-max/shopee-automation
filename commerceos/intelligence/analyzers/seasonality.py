"""Seasonality helpers.

Placeholder for future seasonality models. For WP2.3 we expose a simple day-of-week
index and weekday/weekend flag.
"""

from datetime import date, datetime, timezone
from typing import Dict


DOW_LABELS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def seasonality_context(value_date: date) -> Dict[str, str]:
    """Return deterministic seasonality context for a date."""
    return {
        "day_of_week": DOW_LABELS[value_date.weekday()],
        "is_weekend": str(value_date.weekday() >= 5),
    }


def seasonality_note(value_date: date) -> str:
    """Return a short note about the day type."""
    ctx = seasonality_context(value_date)
    return f"Reference day is {ctx['day_of_week']} (weekend={ctx['is_weekend']})."
