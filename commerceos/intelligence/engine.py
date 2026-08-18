"""Deterministic insight generation.

Converts KPI history, Commerce State, and monitoring signals into explainable
business insights. No LLM dependency.
"""
from commerceos.shared.value_objects.primitives import utc_now

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from commerceos.commerce.models import KPI, CommerceState
from commerceos.intelligence.analyzers.anomalies import evaluate_anomalies
from commerceos.intelligence.analyzers.trends import calculate_trends, group_by_date
from commerceos.intelligence.constants import InsightCategory, InsightSeverity, TrendPeriod, worst_severity
from commerceos.intelligence.explainers.advertising import explain_advertising
from commerceos.intelligence.explainers.finance import explain_profit
from commerceos.intelligence.explainers.inventory import explain_inventory_summary
from commerceos.intelligence.explainers.revenue import explain_revenue_change
from commerceos.intelligence.models import Insight, TrendSnapshot
from commerceos.intelligence.repositories import IntelligenceUnitOfWork
from commerceos.intelligence.sqlalchemy_repositories import SQLAlchemyIntelligenceUnitOfWork
from commerceos.kpi.engine import KPIEngine


# Metrics we use for trend and anomaly analysis
CORE_METRICS = [
    ("gross_sales", "sum"),
    ("net_sales", "sum"),
    ("order_count", "sum"),
    ("aov", "avg"),
    ("gross_profit", "sum"),
    ("gross_margin_pct", "avg"),
    ("shopee_fees", "sum"),
    ("ad_spend", "sum"),
    ("ad_revenue", "sum"),
    ("roas", "avg"),
    ("ctr", "avg"),
]


class IntelligenceEngine:
    """Generate deterministic insights from KPIs and Commerce State."""

    def __init__(
        self,
        session: Session,
        uow: Optional[IntelligenceUnitOfWork] = None,
    ):
        self.session = session
        self.uow = uow or SQLAlchemyIntelligenceUnitOfWork(session)

    def refresh(
        self,
        store_id: str,
        reference_date: Optional[date] = None,
        currency: str = "IDR",
    ) -> Dict[str, Any]:
        """Run full intelligence refresh and persist insights + trend snapshots."""
        reference_date = reference_date or self._today()

        # 1. Load KPIs
        kpi_series = self._load_kpi_series(store_id)

        # 2. Calculate trends
        trends = self._calculate_all_trends(kpi_series, reference_date)

        # 3. Detect anomalies
        anomalies = evaluate_anomalies(trends)

        # 4. Generate explainers
        explainers = self._generate_explainers(kpi_series, reference_date, currency)

        # 5. Monitoring / data quality insights (placeholder)
        operational = self._generate_operational_insights(store_id)

        # 6. Combine and deduplicate by category+title
        all_candidates = anomalies + explainers + operational
        insights = self._deduplicate_candidates(all_candidates)

        # 7. Persist
        with self.uow:
            trend_models = [self._trend_point_to_model(tp) for tp in trends]
            self.uow.trends().save_many(trend_models)
            insight_models = [
                Insight(
                    category=c["category"],
                    severity=c["severity"],
                    title=c["title"],
                    explanation=c["explanation"],
                    evidence=c.get("evidence", {}),
                    expires_at=utc_now() + timedelta(days=1),
                    metadata_={"store_id": store_id, "reference_date": reference_date.isoformat()},
                )
                for c in insights
            ]
            self.uow.insights().save_many(insight_models)

        return {
            "store_id": store_id,
            "reference_date": reference_date.isoformat(),
            "insight_count": len(insight_models),
            "trend_count": len(trend_models),
            "insights": [i.id for i in insight_models],
        }

    def _load_kpi_series(self, store_id: str) -> Dict[str, List[Tuple[datetime, float]]]:
        """Load KPI history as (freshness, value) series by code."""
        kpis = (
            self.session.query(KPI)
            .filter_by(store_id=store_id)
            .order_by(KPI.freshness.asc())
            .all()
        )
        series: Dict[str, List[Tuple[datetime, float]]] = {}
        for kpi in kpis:
            series.setdefault(kpi.code, []).append((kpi.freshness, float(kpi.value)))
        return series

    def _calculate_all_trends(
        self,
        series: Dict[str, List[Tuple[datetime, float]]],
        reference_date: date,
    ) -> List:
        points = []
        for metric, mode in CORE_METRICS:
            values = series.get(metric, [])
            if not values:
                continue
            points.extend(calculate_trends(metric, values, mode=mode, reference_date=reference_date))
        return points

    def _generate_explainers(
        self,
        series: Dict[str, List[Tuple[datetime, float]]],
        reference_date: date,
        currency: str,
    ) -> List[Dict[str, Any]]:
        insights = []
        current, previous = self._today_and_previous(series, reference_date)
        revenue = explain_revenue_change(current, previous, currency)
        if revenue:
            insights.append(revenue)
        profit = explain_profit(current, previous, currency)
        if profit:
            insights.append(profit)
        ads = explain_advertising(current, previous, currency)
        if ads:
            insights.append(ads)
        return insights

    def _today_and_previous(
        self,
        series: Dict[str, List[Tuple[datetime, float]]],
        reference_date: date,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        current = {}
        previous = {}
        for metric, mode in CORE_METRICS:
            values = series.get(metric, [])
            if not values:
                continue
            by_date = group_by_date(values) if mode == "sum" else self._average_by_date(values)
            current[metric] = by_date.get(reference_date)
            previous[metric] = by_date.get(reference_date - timedelta(days=1))
        return current, previous

    def _average_by_date(self, values: List[Tuple[datetime, float]]) -> Dict[date, float]:
        from commerceos.intelligence.analyzers.trends import average_by_date as _avg
        return _avg(values)

    def _generate_operational_insights(self, store_id: str) -> List[Dict[str, Any]]:
        """Generate operational insights from monitoring and data freshness."""
        state = KPIEngine.latest_commerce_state(self.session, store_id)
        insights = []
        if state is None:
            insights.append({
                "category": InsightCategory.OPERATIONS.value,
                "severity": InsightSeverity.WARNING.value,
                "title": "No Commerce State available",
                "explanation": "Commerce State has not been generated. Run KPI refresh to produce insights.",
                "evidence": {"store_id": store_id},
            })
            return insights

        if state.sources_stale:
            insights.append({
                "category": InsightCategory.OPERATIONS.value,
                "severity": InsightSeverity.NOTICE.value,
                "title": f"{len(state.sources_stale)} data sources are stale",
                "explanation": f"Stale sources: {', '.join(state.sources_stale)}. Sync soon to keep intelligence accurate.",
                "evidence": {"stale_sources": state.sources_stale},
            })
        return insights

    def _deduplicate_candidates(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        out = []
        for c in candidates:
            key = (c["category"], c["title"])
            if key in seen:
                continue
            seen.add(key)
            out.append(c)
        return out

    def _trend_point_to_model(self, point) -> TrendSnapshot:
        return TrendSnapshot(
            metric=point.metric,
            period=point.period.value,
            value=point.value,
            baseline=point.baseline,
            delta=point.delta,
            metadata_={"delta_pct": point.delta_pct},
        )

    def _today(self) -> date:
        return utc_now().date()
