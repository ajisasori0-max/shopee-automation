"""Intelligence dashboard read API.

Stable interface for Streamlit and other dashboard consumers. All reads go
through IntelligenceEngine / repositories; no direct model access.
"""
from commerceos.shared.value_objects.primitives import utc_now

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from commerceos.intelligence.constants import InsightSeverity, worst_severity
from commerceos.intelligence.models import Insight, TrendSnapshot
from commerceos.intelligence.repositories import IntelligenceUnitOfWork
from commerceos.intelligence.sqlalchemy_repositories import SQLAlchemyIntelligenceUnitOfWork


class IntelligenceDashboard:
    """Stable read-only dashboard API for the intelligence layer."""

    def __init__(self, uow: IntelligenceUnitOfWork):
        self.uow = uow

    def get_daily_insights(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return recent insights from the last 24 hours."""
        since = utc_now() - timedelta(hours=24)
        insights = self.uow.insights().list(since=since, limit=limit)
        return [_insight_to_dict(i) for i in insights]

    def get_priority_insights(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Return the highest-severity recent insights."""
        since = utc_now() - timedelta(hours=24)
        insights = self.uow.insights().list(since=since, limit=100)
        ranked = sorted(
            insights,
            key=lambda i: InsightSeverity(i.severity).value if i.severity in InsightSeverity._value2member_map_ else "",
            reverse=True,
        )
        return [_insight_to_dict(i) for i in ranked[:limit]]

    def get_trend_summary(self, metrics: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Return latest trend snapshot per metric and period."""
        snapshots = self.uow.trends().list(limit=1000)
        latest: Dict[str, Dict[str, TrendSnapshot]] = {}
        for snap in snapshots:
            latest.setdefault(snap.metric, {})[snap.period] = snap
        result = []
        for metric, periods in latest.items():
            if metrics and metric not in metrics:
                continue
            for period, snap in periods.items():
                result.append(_trend_to_dict(snap))
        return sorted(result, key=lambda x: (x["metric"], x["period"]))

    def get_business_summary(self) -> Dict[str, Any]:
        """Return a high-level business summary from latest insights."""
        insights = self.uow.insights().latest_by_category()
        by_category: Dict[str, List[Dict[str, Any]]] = {}
        for i in insights:
            by_category.setdefault(i.category, []).append(_insight_to_dict(i))
        overall_severity = worst_severity([i.severity for i in insights]).value if insights else InsightSeverity.INFO.value
        return {
            "overall_severity": overall_severity,
            "insight_count": len(insights),
            "categories": by_category,
            "generated_at": utc_now().isoformat(),
        }


def _insight_to_dict(insight: Insight) -> Dict[str, Any]:
    return {
        "id": insight.id,
        "category": insight.category,
        "severity": insight.severity,
        "title": insight.title,
        "explanation": insight.explanation,
        "evidence": insight.evidence,
        "created_at": insight.created_at.isoformat() if insight.created_at else None,
        "expires_at": insight.expires_at.isoformat() if insight.expires_at else None,
        "acknowledged": insight.acknowledged,
    }


def _trend_to_dict(snap: TrendSnapshot) -> Dict[str, Any]:
    return {
        "id": snap.id,
        "metric": snap.metric,
        "period": snap.period,
        "value": float(snap.value) if snap.value is not None else None,
        "baseline": float(snap.baseline) if snap.baseline is not None else None,
        "delta": float(snap.delta) if snap.delta is not None else None,
        "delta_pct": snap.metadata_.get("delta_pct") if snap.metadata_ else None,
        "generated_at": snap.generated_at.isoformat() if snap.generated_at else None,
    }


def get_daily_insights(uow: IntelligenceUnitOfWork, limit: int = 20) -> List[Dict[str, Any]]:
    return IntelligenceDashboard(uow).get_daily_insights(limit=limit)


def get_priority_insights(uow: IntelligenceUnitOfWork, limit: int = 5) -> List[Dict[str, Any]]:
    return IntelligenceDashboard(uow).get_priority_insights(limit=limit)


def get_trend_summary(uow: IntelligenceUnitOfWork, metrics: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    return IntelligenceDashboard(uow).get_trend_summary(metrics=metrics)


def get_business_summary(uow: IntelligenceUnitOfWork) -> Dict[str, Any]:
    return IntelligenceDashboard(uow).get_business_summary()
