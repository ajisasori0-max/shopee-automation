"""Shared enumerations and status helpers for the intelligence layer."""

from enum import Enum


class InsightCategory(str, Enum):
    REVENUE = "revenue"
    PROFIT = "profit"
    ADVERTISING = "advertising"
    INVENTORY = "inventory"
    OPERATIONS = "operations"
    MONITORING = "monitoring"
    DATA_QUALITY = "data_quality"


class InsightSeverity(str, Enum):
    INFO = "info"
    NOTICE = "notice"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


class TrendPeriod(str, Enum):
    DAY_OVER_DAY = "day_over_day"
    WEEK_OVER_WEEK = "week_over_week"
    MONTH_OVER_MONTH = "month_over_month"
    ROLLING_7D = "rolling_7d"
    ROLLING_30D = "rolling_30d"


def severity_rank(severity) -> int:
    return {
        InsightSeverity.INFO: 0,
        InsightSeverity.NOTICE: 1,
        InsightSeverity.WARNING: 2,
        InsightSeverity.HIGH: 3,
        InsightSeverity.CRITICAL: 4,
    }.get(severity if isinstance(severity, InsightSeverity) else InsightSeverity(severity), 0)


def worst_severity(severities) -> InsightSeverity:
    ranked = sorted(
        [s if isinstance(s, InsightSeverity) else InsightSeverity(s) for s in severities if s],
        key=severity_rank,
        reverse=True,
    )
    return ranked[0] if ranked else InsightSeverity.INFO
