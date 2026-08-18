"""Unit tests for the decision intelligence layer."""

import datetime
from decimal import Decimal

import pytest

from commerceos.intelligence.analyzers.comparisons import compare_metrics, describe_change, format_currency, format_pct
from commerceos.intelligence.analyzers.growth import compound_growth_rate, growth_rate
from commerceos.intelligence.analyzers.seasonality import seasonality_context, seasonality_note
from commerceos.intelligence.analyzers.trends import (
    average_by_date,
    calculate_trends,
    detect_anomaly,
    group_by_date,
    rolling_average,
)
from commerceos.intelligence.constants import InsightCategory, InsightSeverity, TrendPeriod
from commerceos.intelligence.explainers.advertising import explain_advertising, ROAS_THRESHOLD
from commerceos.intelligence.explainers.finance import explain_profit, PROFIT_MARGIN_THRESHOLD
from commerceos.intelligence.explainers.revenue import explain_revenue_change


class TestTrendCalculations:
    def test_group_by_date(self):
        base = datetime.datetime(2026, 7, 24, 0, 0, 0, tzinfo=datetime.timezone.utc)
        values = [(base + datetime.timedelta(hours=3 * i), 100.0) for i in range(4)]
        grouped = group_by_date(values)
        assert grouped == {base.date(): 400.0}

    def test_rolling_average(self):
        series = {
            datetime.date(2026, 7, 23): 100.0,
            datetime.date(2026, 7, 22): 200.0,
            datetime.date(2026, 7, 21): 300.0,
        }
        target = datetime.date(2026, 7, 24)
        avg = rolling_average(series, 3, target)
        assert avg == 200.0

    def test_calculate_trends_day_over_day(self):
        base = datetime.datetime(2026, 7, 24, 0, 0, 0, tzinfo=datetime.timezone.utc)
        values = [
            (base - datetime.timedelta(days=1), 100.0),
            (base, 150.0),
        ]
        trends = calculate_trends("revenue", values, mode="sum", reference_date=base.date())
        by_period = {t.period: t for t in trends}
        assert by_period[TrendPeriod.DAY_OVER_DAY].value == 150.0
        assert by_period[TrendPeriod.DAY_OVER_DAY].baseline == 100.0
        assert by_period[TrendPeriod.DAY_OVER_DAY].delta_pct == 50.0

    def test_calculate_trends_rolling_7d(self):
        base = datetime.datetime(2026, 7, 24, 0, 0, 0, tzinfo=datetime.timezone.utc)
        values = [
            (base - datetime.timedelta(days=7), 100.0),
            (base - datetime.timedelta(days=6), 100.0),
            (base - datetime.timedelta(days=5), 100.0),
            (base - datetime.timedelta(days=4), 100.0),
            (base - datetime.timedelta(days=3), 100.0),
            (base - datetime.timedelta(days=2), 100.0),
            (base - datetime.timedelta(days=1), 100.0),
            (base, 200.0),
        ]
        trends = calculate_trends("revenue", values, mode="sum", reference_date=base.date())
        by_period = {t.period: t for t in trends}
        assert by_period[TrendPeriod.ROLLING_7D].value == 200.0
        assert by_period[TrendPeriod.ROLLING_7D].baseline == 100.0


class TestAnomalyDetection:
    def test_detect_anomaly_both_directions(self):
        assert detect_anomaly(150, 100, 0.30) is True
        assert detect_anomaly(105, 100, 0.30) is False
        assert detect_anomaly(50, 100, 0.30) is True

    def test_detect_anomaly_directional(self):
        assert detect_anomaly(150, 100, 0.30, direction="up") is True
        assert detect_anomaly(50, 100, 0.30, direction="up") is False
        assert detect_anomaly(50, 100, 0.30, direction="down") is True


class TestComparisons:
    def test_compare_metrics(self):
        current = {"revenue": 150, "orders": 10}
        previous = {"revenue": 100, "orders": 10}
        result = compare_metrics(current, previous)
        assert result["revenue"]["delta"] == 50
        assert result["revenue"]["delta_pct"] == 50.0
        assert result["orders"]["delta_pct"] == 0.0

    def test_describe_change(self):
        assert describe_change(0.5) == "remained stable"
        assert describe_change(15) == "increased sharply"
        assert describe_change(-15) == "decreased sharply"


class TestExplainers:
    def test_revenue_change(self):
        current = {"gross_sales": 150, "order_count": 10, "aov": 15}
        previous = {"gross_sales": 100, "order_count": 10, "aov": 10}
        result = explain_revenue_change(current, previous)
        assert result["category"] == InsightCategory.REVENUE.value
        assert "50.0%" in result["title"]
        assert "Rp 150" in result["explanation"]

    def test_profit_change(self):
        current = {"gross_profit": 100, "gross_margin_pct": 0.05}
        previous = {"gross_profit": 200, "gross_margin_pct": 0.05}
        result = explain_profit(current, previous)
        assert result["category"] == InsightCategory.PROFIT.value
        assert result["severity"] == InsightSeverity.HIGH.value

    def test_advertising_low_roas(self):
        current = {"ad_spend": 100, "roas": 1.5}
        previous = {"ad_spend": 100, "roas": 2.5}
        result = explain_advertising(current, previous)
        assert result["category"] == InsightCategory.ADVERTISING.value
        assert result["severity"] == InsightSeverity.HIGH.value


class TestSeasonality:
    def test_seasonality_context(self):
        ctx = seasonality_context(datetime.date(2026, 7, 24))  # Friday
        assert ctx["day_of_week"] == "Friday"
        assert ctx["is_weekend"] == "False"

    def test_seasonality_note(self):
        note = seasonality_note(datetime.date(2026, 7, 25))  # Saturday
        assert "Saturday" in note


class TestGrowth:
    def test_growth_rate(self):
        assert growth_rate(150, 100) == 50.0
        assert growth_rate(None, 100) is None

    def test_compound_growth_rate(self):
        assert compound_growth_rate([100, 200], 1) == 100.0
        assert compound_growth_rate([100, 200], 2) is not None


def test_format_currency():
    assert "Rp" in format_currency(12345, "IDR")
    assert "N/A" in format_currency(None, "IDR")


def test_format_pct():
    assert format_pct(5.5) == "+5.5%"
    assert format_pct(-5.5) == "-5.5%"
