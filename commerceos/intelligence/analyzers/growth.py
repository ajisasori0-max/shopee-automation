"""Growth analysis helpers."""

from typing import List, Optional


def compound_growth_rate(values: List[float], periods: int) -> Optional[float]:
    """CAGR-style growth over `periods` intervals."""
    if not values or len(values) < 2 or periods == 0:
        return None
    start = float(values[0])
    end = float(values[-1])
    if start == 0:
        return None
    return ((end / start) ** (1 / periods) - 1) * 100


def growth_rate(current: Optional[float], previous: Optional[float]) -> Optional[float]:
    if current is None or previous is None or previous == 0:
        return None
    return (current - previous) / previous * 100
