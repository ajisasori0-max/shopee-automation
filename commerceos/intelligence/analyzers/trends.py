"""Trend analysis helpers.

Deterministic calculations only: rolling averages, deltas, and baseline
comparisons. No machine learning.
"""
from commerceos.shared.value_objects.primitives import utc_now

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from statistics import mean
from typing import Dict, List, Optional, Tuple

from commerceos.intelligence.constants import TrendPeriod


@dataclass
class TrendPoint:
    metric: str
    period: TrendPeriod
    value: Optional[float]
    baseline: Optional[float]
    delta: Optional[float]
    delta_pct: Optional[float]


def _to_date(value: datetime) -> date:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).date()


def group_by_date(values: List[Tuple[datetime, float]]) -> Dict[date, float]:
    """Sum values by UTC date."""
    out: Dict[date, float] = {}
    for ts, v in values:
        d = _to_date(ts)
        out[d] = out.get(d, 0.0) + float(v)
    return out


def average_by_date(values: List[Tuple[datetime, float]]) -> Dict[date, float]:
    """Average values by UTC date."""
    sums: Dict[date, float] = {}
    counts: Dict[date, int] = {}
    for ts, v in values:
        d = _to_date(ts)
        sums[d] = sums.get(d, 0.0) + float(v)
        counts[d] = counts.get(d, 0) + 1
    return {d: sums[d] / counts[d] for d in sums}


def rolling_average(series: Dict[date, float], window: int, target: date) -> Optional[float]:
    """Average of `window` days ending the day before `target`."""
    days = [target - timedelta(days=i) for i in range(1, window + 1)]
    vals = [series.get(d) for d in days]
    vals = [v for v in vals if v is not None]
    if not vals:
        return None
    return mean(vals)


def calculate_trends(
    metric: str,
    values: List[Tuple[datetime, float]],
    mode: str = "sum",
    reference_date: Optional[date] = None,
) -> List[TrendPoint]:
    """Calculate trend points for all supported periods.

    `mode` is either 'sum' (e.g. revenue, spend) or 'avg' (e.g. ROAS, CTR).
    """
    reference_date = reference_date or _to_date(utc_now())
    series = group_by_date(values) if mode == "sum" else average_by_date(values)

    points: List[TrendPoint] = []
    for period in TrendPeriod:
        point = _calculate_trend_point(metric, period, series, reference_date)
        points.append(point)
    return points


def _calculate_trend_point(
    metric: str,
    period: TrendPeriod,
    series: Dict[date, float],
    reference_date: date,
) -> TrendPoint:
    if period == TrendPeriod.DAY_OVER_DAY:
        current = series.get(reference_date)
        baseline = series.get(reference_date - timedelta(days=1))
    elif period == TrendPeriod.WEEK_OVER_WEEK:
        current = series.get(reference_date)
        baseline = series.get(reference_date - timedelta(days=7))
    elif period == TrendPeriod.MONTH_OVER_MONTH:
        current = series.get(reference_date)
        baseline = series.get(reference_date - timedelta(days=30))
    elif period == TrendPeriod.ROLLING_7D:
        current = series.get(reference_date)
        baseline = rolling_average(series, 7, reference_date)
    elif period == TrendPeriod.ROLLING_30D:
        current = series.get(reference_date)
        baseline = rolling_average(series, 30, reference_date)
    else:
        current = baseline = None

    delta = (current - baseline) if current is not None and baseline is not None else None
    delta_pct = (delta / baseline * 100) if delta is not None and baseline else None
    return TrendPoint(
        metric=metric,
        period=period,
        value=current,
        baseline=baseline,
        delta=delta,
        delta_pct=delta_pct,
    )


def detect_anomaly(
    current: Optional[float],
    baseline: Optional[float],
    threshold_pct: float,
    direction: str = "both",
) -> bool:
    """Return True if current deviates from baseline by more than threshold_pct."""
    if current is None or baseline is None or baseline == 0:
        return False
    if direction == "both":
        return abs(current - baseline) / baseline >= threshold_pct
    if direction == "up":
        return (current - baseline) / baseline >= threshold_pct
    if direction == "down":
        return (baseline - current) / baseline >= threshold_pct
    return False
