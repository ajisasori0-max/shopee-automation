"""Dashboard Query Service — stable read API for the Streamlit UI.

All Streamlit pages consume this service. Pages never touch SQLAlchemy models,
legacy engines, or Shopee APIs directly. E1.4 introduced the KPI Engine and
CommerceState tables; this service reads from precomputed materialized KPIs
first, and falls back to canonical table computation only when no KPIs exist.

Method labels:
- **Materialized**: reads from KPI / CommerceState tables (E1.4+).
- **Temporary**: computed directly from canonical tables. Fallback only.
- **Compatibility**: wraps a legacy dependency with a clear removal plan.
"""
from __future__ import annotations
from commerceos.shared.value_objects.primitives import utc_now


from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from commerceos.commerce.models import (
    Ad,
    AdPerformance,
    Campaign,
    CommerceState,
    KPI,
    Order,
    OrderItem,
    Payment,
    Product,
    Store,
)
from commerceos.ingestion.audit import (
    find_missing_provenance,
    provenance_report,
    raw_payload_summary,
    sync_run_report,
)
from commerceos.ingestion.models import SyncCheckpoint, SyncRun
from commerceos.kpi.engine import KPIEngine
from commerceos.platform.database.connection import get_session
from commerceos.config.settings import get_settings


class DashboardQueryService:
    """Read-only service for all dashboard widgets."""

    def __init__(self, session: Optional[Session] = None, database_url: Optional[str] = None):
        settings = get_settings()
        self._database_url = database_url or settings.database_url
        self._session = session or get_session(self._database_url)
        self._owns_session = session is None
        self._kpi_engine = KPIEngine(self._session)

    def __enter__(self) -> "DashboardQueryService":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._owns_session:
            self._session.close()

    @property
    def session(self) -> Session:
        return self._session

    def refresh(self, store_id: str, organization_id: str, business_id: str) -> Dict[str, Any]:
        """Materialize KPIs and CommerceState for the store."""
        return self._kpi_engine.refresh(store_id, organization_id, business_id)

    # ------------------------------------------------------------------
    # Materialized (E1.4): Commerce State
    # ------------------------------------------------------------------

    def get_commerce_state(self, store_id: str) -> Dict[str, Any]:
        """Serve from CommerceState table when available; fallback to temporary."""
        state = KPIEngine.latest_commerce_state(self._session, store_id)
        if state:
            return {
                "store_id": store_id,
                "data_quality_score": float(state.data_quality_score),
                "sources_fresh": state.sources_fresh,
                "sources_stale": state.sources_stale,
                "alerts": state.alerts,
                "last_sync": state.last_sync,
                "summary": state.summary,
                "temporary": False,
            }
        return self._get_commerce_state_temporary(store_id)

    def _get_commerce_state_temporary(self, store_id: str) -> Dict[str, Any]:
        latest_sync = self._get_latest_sync_run(store_id)
        missing_prov = find_missing_provenance(self._session)
        return {
            "store_id": store_id,
            "data_quality_score": float(Decimal("1.0") if not missing_prov else Decimal("0.8")),
            "sources_fresh": ["orders", "payments"] if latest_sync else [],
            "sources_stale": [],
            "alerts": [
                {
                    "type": "missing_provenance",
                    "count": sum(m["missing"] for m in missing_prov),
                    "severity": "warning" if missing_prov else "info",
                }
            ]
            if missing_prov
            else [],
            "last_sync": latest_sync.completed_at.isoformat() if latest_sync and latest_sync.completed_at else None,
            "summary": {},
            "temporary": True,
        }

    # ------------------------------------------------------------------
    # TEMPORARY: Sync Health / Freshness
    # ------------------------------------------------------------------

    def get_sync_health(self, store_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """TEMPORARY: Latest sync status per entity type from sync_runs."""
        runs = sync_run_report(self._session, limit=50)
        if store_id:
            runs = [r for r in runs if r["store_id"] == store_id]
        return runs

    def get_freshness(self, store_id: str) -> Dict[str, Any]:
        """TEMPORARY: Hours since last successful sync per entity type."""
        checkpoints = (
            self._session.query(SyncCheckpoint)
            .filter_by(store_id=store_id)
            .all()
        )
        now = utc_now()
        result = {}
        for cp in checkpoints:
            if cp.last_successful_sync_at:
                ts = cp.last_successful_sync_at
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                hours = (now - ts).total_seconds() / 3600
                result[cp.entity_type] = {
                    "hours_since_sync": round(hours, 2),
                    "is_fresh": hours < 24,
                    "last_sync": cp.last_successful_sync_at.isoformat(),
                }
        return result

    def get_data_quality_summary(self, store_id: str) -> Dict[str, Any]:
        """TEMPORARY: Missing provenance + recent failure count."""
        missing = find_missing_provenance(self._session)
        failures = (
            self._session.query(SyncRun)
            .filter_by(store_id=store_id, status="failed")
            .order_by(SyncRun.created_at.desc())
            .limit(5)
            .all()
        )
        return {
            "missing_provenance": missing,
            "recent_failures": [
                {
                    "entity_type": f.entity_type,
                    "errors": f.errors,
                    "failed_at": f.completed_at.isoformat() if f.completed_at else None,
                }
                for f in failures
            ],
        }

    # ------------------------------------------------------------------
    # Materialized (E1.4): Orders / Financial Metrics
    # ------------------------------------------------------------------

    def _kpis_in_range(self, store_id: str, start: datetime, end: datetime, codes: List[str]) -> List[KPI]:
        return (
            self._session.query(KPI)
            .filter(
                KPI.store_id == store_id,
                KPI.code.in_(codes),
                KPI.freshness >= start,
                KPI.freshness <= end,
            )
            .all()
        )

    def get_daily_sales(self, store_id: str, start: datetime, end: datetime) -> List[Dict[str, Any]]:
        """Daily sales trend from materialized KPIs; fallback to canonical."""
        kpis = self._kpis_in_range(
            store_id, start, end, ["gross_sales", "net_income", "order_count"]
        )
        if kpis:
            return self._daily_sales_from_kpis(kpis)
        return self._get_daily_sales_temporary(store_id, start, end)

    def _daily_sales_from_kpis(self, kpis: List[KPI]) -> List[Dict[str, Any]]:
        by_day: Dict[str, Dict[str, Any]] = {}
        for kpi in kpis:
            day = kpi.freshness.date().isoformat()
            by_day.setdefault(day, {"date": day})
            if kpi.code == "gross_sales":
                by_day[day]["gross_sales"] = float(kpi.value)
            elif kpi.code == "net_income":
                by_day[day]["net_income"] = float(kpi.value)
            elif kpi.code == "order_count":
                by_day[day]["order_count"] = int(kpi.value)
        return [
            {
                "date": d["date"],
                "gross_sales": d.get("gross_sales", 0.0),
                "net_income": d.get("net_income", 0.0),
                "order_count": d.get("order_count", 0),
            }
            for d in sorted(by_day.values(), key=lambda x: x["date"])
        ]

    def _get_daily_sales_temporary(self, store_id: str, start: datetime, end: datetime) -> List[Dict[str, Any]]:
        stmt = (
            select(
                func.date(Order.ordered_at).label("date"),
                func.count(Order.id).label("order_count"),
                func.sum(Order.total_amount).label("gross_sales"),
                func.sum(Payment.net_amount).label("net_income"),
            )
            .outerjoin(Payment, Payment.order_id == Order.id)
            .where(
                Order.store_id == store_id,
                Order.ordered_at >= start,
                Order.ordered_at <= end,
            )
            .group_by(func.date(Order.ordered_at))
            .order_by(func.date(Order.ordered_at))
        )
        rows = self._session.execute(stmt).all()
        return [
            {
                "date": row.date,
                "order_count": row.order_count,
                "gross_sales": float(row.gross_sales or 0),
                "net_income": float(row.net_income or 0),
            }
            for row in rows
        ]

    def get_pl_summary(self, store_id: str, start: datetime, end: datetime) -> Dict[str, Any]:
        """P&L summary from materialized KPIs; fallback to canonical."""
        codes = [
            "gross_sales",
            "discounts",
            "net_sales",
            "shopee_fees",
            "gross_profit",
            "gross_margin_pct",
            "aov",
            "order_count",
        ]
        kpis = self._kpis_in_range(store_id, start, end, codes)
        if kpis:
            return self._pl_summary_from_kpis(kpis)
        return self._get_pl_summary_temporary(store_id, start, end)

    def _pl_summary_from_kpis(self, kpis: List[KPI]) -> Dict[str, Any]:
        by_code = {k.code: k for k in kpis}
        net_sales = by_code.get("net_sales", KPI(value=Decimal("0"))).value
        gross_profit = by_code.get("gross_profit", KPI(value=Decimal("0"))).value
        gross_sales = by_code.get("gross_sales", KPI(value=Decimal("0"))).value
        order_count = int(by_code.get("order_count", KPI(value=Decimal("0"))).value)
        margin = by_code.get("gross_margin_pct", KPI(value=Decimal("0"))).value
        aov = by_code.get("aov", KPI(value=Decimal("0"))).value
        return {
            "order_count": order_count,
            "gross_sales": float(gross_sales),
            "discounts": float(by_code.get("discounts", KPI(value=Decimal("0"))).value),
            "net_sales": float(net_sales),
            "shopee_fees": float(by_code.get("shopee_fees", KPI(value=Decimal("0"))).value),
            "gross_profit": float(gross_profit),
            "gross_margin_pct": float(margin),
            "aov": float(aov),
            "temporary": False,
        }

    def _get_pl_summary_temporary(self, store_id: str, start: datetime, end: datetime) -> Dict[str, Any]:
        stmt = (
            select(
                func.count(Order.id).label("order_count"),
                func.sum(Order.total_amount).label("gross_sales"),
                func.sum(Order.discount).label("discounts"),
                func.sum(Order.shipping_cost).label("shipping"),
                func.sum(Payment.gross_amount).label("payment_gross"),
                func.sum(Payment.fee_amount).label("payment_fees"),
                func.sum(Payment.net_amount).label("payment_net"),
            )
            .outerjoin(Payment, Payment.order_id == Order.id)
            .where(
                Order.store_id == store_id,
                Order.ordered_at >= start,
                Order.ordered_at <= end,
            )
        )
        row = self._session.execute(stmt).first()

        gross_sales = Decimal(str(row.gross_sales or 0))
        discounts = Decimal(str(row.discounts or 0))
        payment_fees = Decimal(str(row.payment_fees or 0))
        net_sales = gross_sales - discounts
        gross_profit = net_sales - payment_fees

        return {
            "order_count": row.order_count or 0,
            "gross_sales": float(gross_sales),
            "discounts": float(discounts),
            "net_sales": float(net_sales),
            "shopee_fees": float(payment_fees),
            "gross_profit": float(gross_profit),
            "gross_margin_pct": float((gross_profit / net_sales * 100) if net_sales else 0),
            "aov": float(gross_sales / (row.order_count or 1)),
            "temporary": True,
        }

    def get_ad_performance_summary(self, store_id: str, start: datetime, end: datetime) -> Dict[str, Any]:
        """Ads metrics from materialized KPIs; fallback to canonical."""
        codes = [
            "ad_spend",
            "ad_revenue",
            "ad_impressions",
            "ad_clicks",
            "ad_conversions",
            "roas",
            "ctr",
        ]
        kpis = self._kpis_in_range(store_id, start, end, codes)
        if kpis:
            return self._ad_summary_from_kpis(kpis)
        return self._get_ad_summary_temporary(store_id, start, end)

    def _ad_summary_from_kpis(self, kpis: List[KPI]) -> Dict[str, Any]:
        by_code = {k.code: k for k in kpis}
        spend = by_code.get("ad_spend", KPI(value=Decimal("0"))).value
        revenue = by_code.get("ad_revenue", KPI(value=Decimal("0"))).value
        roas = by_code.get("roas", KPI(value=Decimal("0"))).value
        ctr = by_code.get("ctr", KPI(value=Decimal("0"))).value
        return {
            "total_spend": float(spend),
            "total_revenue": float(revenue),
            "total_impressions": int(by_code.get("ad_impressions", KPI(value=Decimal("0"))).value),
            "total_clicks": int(by_code.get("ad_clicks", KPI(value=Decimal("0"))).value),
            "total_conversions": int(by_code.get("ad_conversions", KPI(value=Decimal("0"))).value),
            "roas": float(roas),
            "ctr": float(ctr),
            "temporary": False,
        }

    def _get_ad_summary_temporary(self, store_id: str, start: datetime, end: datetime) -> Dict[str, Any]:
        stmt = (
            select(
                func.sum(AdPerformance.spend).label("total_spend"),
                func.sum(AdPerformance.revenue).label("total_revenue"),
                func.sum(AdPerformance.impressions).label("total_impressions"),
                func.sum(AdPerformance.clicks).label("total_clicks"),
                func.sum(AdPerformance.conversions).label("total_conversions"),
            )
            .where(
                AdPerformance.store_id == store_id,
                AdPerformance.date >= start,
                AdPerformance.date <= end,
            )
        )
        row = self._session.execute(stmt).first()

        spend = Decimal(str(row.total_spend or 0))
        revenue = Decimal(str(row.total_revenue or 0))
        clicks = row.total_clicks or 0
        impressions = row.total_impressions or 0

        return {
            "total_spend": float(spend),
            "total_revenue": float(revenue),
            "total_impressions": impressions,
            "total_clicks": clicks,
            "total_conversions": row.total_conversions or 0,
            "roas": float(revenue / spend) if spend else 0.0,
            "ctr": float(clicks / impressions * 100) if impressions else 0.0,
            "temporary": True,
        }

    def get_order_list(self, store_id: str, start: datetime, end: datetime, limit: int = 100) -> List[Dict[str, Any]]:
        """TEMPORARY: Order list from canonical Order."""
        orders = (
            self._session.query(Order)
            .filter(
                Order.store_id == store_id,
                Order.ordered_at >= start,
                Order.ordered_at <= end,
            )
            .order_by(Order.ordered_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "order_sn": o.marketplace_order_id,
                "status": o.status,
                "total_amount": float(o.total_amount),
                "ordered_at": o.ordered_at.isoformat() if o.ordered_at else None,
                "item_count": len(o.items) if o.items else 0,
            }
            for o in orders
        ]

    # ------------------------------------------------------------------
    # Materialized (E1.4): KPIs
    # ------------------------------------------------------------------

    def get_kpi(self, store_id: str, code: str) -> Optional[Dict[str, Any]]:
        """Read a single KPI by code from the materialized table."""
        now = utc_now()
        kpi = (
            self._session.query(KPI)
            .filter(
                KPI.store_id == store_id,
                KPI.code == code,
                KPI.freshness >= now - timedelta(days=30),
                KPI.freshness <= now,
            )
            .order_by(KPI.freshness.desc())
            .first()
        )
        if kpi:
            return {
                "code": kpi.code,
                "name": kpi.name,
                "value": float(kpi.value),
                "unit": kpi.unit,
                "freshness": kpi.freshness.isoformat(),
                "temporary": False,
            }
        # Fallback to legacy behavior
        if code == "net_sales":
            return self.get_pl_summary(store_id, now - timedelta(days=30), now)
        if code == "roas":
            return self.get_ad_performance_summary(store_id, now - timedelta(days=30), now)
        return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_latest_sync_run(self, store_id: str) -> Optional[SyncRun]:
        return (
            self._session.query(SyncRun)
            .filter_by(store_id=store_id, status="completed")
            .order_by(SyncRun.completed_at.desc())
            .first()
        )


