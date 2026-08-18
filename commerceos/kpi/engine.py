"""KPI Engine — computes, persists, and refreshes daily KPIs from canonical tables.

Design:
- KPIs are materialized per (store_id, date, code) for fast dashboard reads.
- Aggregations roll up by date; the DashboardQueryService sums/averages across
  arbitrary date ranges.
- KPIHistory records every refresh so we can trend confidence/freshness.
"""
from __future__ import annotations
from commerceos.shared.value_objects.primitives import utc_now


from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple, Union

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from commerceos.commerce.models import (
    AdPerformance,
    CommerceState,
    DataQualityEvent,
    KPI,
    KPIHistory,
    Order,
    Payment,
)
from commerceos.ingestion.models import SyncCheckpoint
from commerceos.platform.database.models import new_uuid


FRESHNESS_HOURS_THRESHOLD = 24


def _to_date(value: datetime) -> date:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).date()


def _round2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _zero(value: Optional[Union[Decimal, int, float]]) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


class KPIEngine:
    """Materializes daily KPIs and the Commerce State snapshot."""

    def __init__(self, session: Session):
        self.session = session

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def refresh(
        self,
        store_id: str,
        organization_id: str,
        business_id: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Compute and persist KPIs + CommerceState for a store.

        Defaults to the last 30 days so dashboards have a full window.
        """
        end = end or utc_now()
        start = start or (end - timedelta(days=30))

        # Build sales, ad, and P&L KPIs per day
        sales_rows = self._compute_sales_kpis(store_id, start, end)
        pl_rows = self._compute_pl_kpis(store_id, start, end)
        ad_rows = self._compute_ad_kpis(store_id, start, end)

        all_rows = sales_rows + pl_rows + ad_rows
        self._persist_kpis(store_id, organization_id, business_id, all_rows)

        # Build one CommerceState snapshot
        commerce_state = self._build_commerce_state(
            store_id, organization_id, business_id, start, end
        )
        self._persist_commerce_state(commerce_state)

        return {
            "store_id": store_id,
            "kpi_count": len(all_rows),
            "commerce_state_id": commerce_state["id"],
            "date_range": [start.isoformat(), end.isoformat()],
        }

    # ------------------------------------------------------------------
    # Sales KPIs (per order date)
    # ------------------------------------------------------------------

    def _compute_sales_kpis(
        self, store_id: str, start: datetime, end: datetime
    ) -> List[Dict[str, Any]]:
        # Load fees by payment date so daily sales can approximate net income.
        fee_stmt = (
            select(
                func.date(Payment.paid_at).label("day"),
                func.sum(Payment.fee_amount).label("payment_fees"),
            )
            .where(
                Payment.store_id == store_id,
                Payment.paid_at >= start,
                Payment.paid_at <= end,
            )
            .group_by(func.date(Payment.paid_at))
        )
        fee_rows = {r.day: _zero(r.payment_fees) for r in self.session.execute(fee_stmt).all()}

        stmt = (
            select(
                func.date(Order.ordered_at).label("day"),
                func.count(Order.id).label("order_count"),
                func.sum(Order.total_amount).label("gross_sales"),
                func.sum(Order.discount).label("discounts"),
            )
            .where(
                Order.store_id == store_id,
                Order.ordered_at >= start,
                Order.ordered_at <= end,
            )
            .group_by(func.date(Order.ordered_at))
        )
        rows = self.session.execute(stmt).all()
        results = []
        for row in rows:
            day = row.day
            gross = _zero(row.gross_sales)
            disc = _zero(row.discounts)
            net = gross - disc
            fees = fee_rows.get(day, Decimal("0"))
            results.append(
                {
                    "date": day,
                    "code": "gross_sales",
                    "name": "Gross Sales",
                    "value": _round2(gross),
                    "unit": "IDR",
                    "formula": "SUM(order.total_amount)",
                }
            )
            results.append(
                {
                    "date": day,
                    "code": "discounts",
                    "name": "Discounts",
                    "value": _round2(disc),
                    "unit": "IDR",
                    "formula": "SUM(order.discount)",
                }
            )
            results.append(
                {
                    "date": day,
                    "code": "net_sales",
                    "name": "Net Sales",
                    "value": _round2(net),
                    "unit": "IDR",
                    "formula": "gross_sales - discounts",
                }
            )
            results.append(
                {
                    "date": day,
                    "code": "order_count",
                    "name": "Order Count",
                    "value": Decimal(row.order_count or 0),
                    "unit": "orders",
                    "formula": "COUNT(order.id)",
                }
            )
            results.append(
                {
                    "date": day,
                    "code": "net_income",
                    "name": "Net Income",
                    "value": _round2(net - fees),
                    "unit": "IDR",
                    "formula": "net_sales - shopee_fees (by payment date, approximate)",
                }
            )
        return results

    # ------------------------------------------------------------------
    # P&L / Payment KPIs (per payment date)
    # ------------------------------------------------------------------

    def _compute_pl_kpis(
        self, store_id: str, start: datetime, end: datetime
    ) -> List[Dict[str, Any]]:
        # Order-level AOV per day
        aov_stmt = (
            select(
                func.date(Order.ordered_at).label("day"),
                func.sum(Order.total_amount).label("gross_sales"),
                func.count(Order.id).label("order_count"),
            )
            .where(
                Order.store_id == store_id,
                Order.ordered_at >= start,
                Order.ordered_at <= end,
            )
            .group_by(func.date(Order.ordered_at))
        )
        aov_rows = {r.day: r for r in self.session.execute(aov_stmt).all()}

        # Payment fees per day
        fee_stmt = (
            select(
                func.date(Payment.paid_at).label("day"),
                func.sum(Payment.gross_amount).label("payment_gross"),
                func.sum(Payment.fee_amount).label("payment_fees"),
                func.sum(Payment.net_amount).label("payment_net"),
            )
            .where(
                Payment.store_id == store_id,
                Payment.paid_at >= start,
                Payment.paid_at <= end,
            )
            .group_by(func.date(Payment.paid_at))
        )
        fee_rows = {r.day: r for r in self.session.execute(fee_stmt).all()}

        all_days = set(aov_rows.keys()) | set(fee_rows.keys())
        results = []
        for day in sorted(all_days):
            aov_row = aov_rows.get(day)
            fee_row = fee_rows.get(day)
            gross = _zero(aov_row.gross_sales if aov_row else 0)
            orders = aov_row.order_count if aov_row else 0
            fees = _zero(fee_row.payment_fees if fee_row else 0)
            net_payments = _zero(fee_row.payment_net if fee_row else 0)
            aov = _round2(gross / Decimal(orders or 1))
            gross_profit = _round2(gross - fees)
            margin = Decimal("0")
            if gross:
                margin = _round2(gross_profit / gross * 100)

            results.append(
                {
                    "date": day,
                    "code": "shopee_fees",
                    "name": "Shopee Fees",
                    "value": fees,
                    "unit": "IDR",
                    "formula": "SUM(payment.fee_amount)",
                }
            )
            results.append(
                {
                    "date": day,
                    "code": "gross_profit",
                    "name": "Gross Profit",
                    "value": gross_profit,
                    "unit": "IDR",
                    "formula": "net_sales - shopee_fees",
                }
            )
            results.append(
                {
                    "date": day,
                    "code": "gross_margin_pct",
                    "name": "Gross Margin %",
                    "value": margin,
                    "unit": "%",
                    "formula": "gross_profit / gross_sales * 100",
                }
            )
            results.append(
                {
                    "date": day,
                    "code": "aov",
                    "name": "Average Order Value",
                    "value": aov,
                    "unit": "IDR",
                    "formula": "gross_sales / order_count",
                }
            )
            results.append(
                {
                    "date": day,
                    "code": "payment_net",
                    "name": "Net Payments",
                    "value": _round2(net_payments),
                    "unit": "IDR",
                    "formula": "SUM(payment.net_amount)",
                }
            )
        return results

    # ------------------------------------------------------------------
    # Ad KPIs (per performance date)
    # ------------------------------------------------------------------

    def _compute_ad_kpis(
        self, store_id: str, start: datetime, end: datetime
    ) -> List[Dict[str, Any]]:
        stmt = (
            select(
                func.date(AdPerformance.date).label("day"),
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
            .group_by(func.date(AdPerformance.date))
        )
        rows = self.session.execute(stmt).all()
        results = []
        for row in rows:
            day = row.day
            spend = _zero(row.total_spend)
            revenue = _zero(row.total_revenue)
            clicks = row.total_clicks or 0
            impressions = row.total_impressions or 0
            conversions = row.total_conversions or 0
            roas = _round2(revenue / spend) if spend else Decimal("0")
            ctr = Decimal("0")
            if impressions:
                ctr = _round2(Decimal(clicks) / Decimal(impressions) * 100)

            results.append(
                {
                    "date": day,
                    "code": "ad_spend",
                    "name": "Ad Spend",
                    "value": spend,
                    "unit": "IDR",
                    "formula": "SUM(ad_performance.spend)",
                }
            )
            results.append(
                {
                    "date": day,
                    "code": "ad_revenue",
                    "name": "Ad Revenue",
                    "value": revenue,
                    "unit": "IDR",
                    "formula": "SUM(ad_performance.revenue)",
                }
            )
            results.append(
                {
                    "date": day,
                    "code": "roas",
                    "name": "ROAS",
                    "value": roas,
                    "unit": "x",
                    "formula": "ad_revenue / ad_spend",
                }
            )
            results.append(
                {
                    "date": day,
                    "code": "ctr",
                    "name": "CTR",
                    "value": ctr,
                    "unit": "%",
                    "formula": "clicks / impressions * 100",
                }
            )
            results.append(
                {
                    "date": day,
                    "code": "ad_conversions",
                    "name": "Ad Conversions",
                    "value": Decimal(conversions),
                    "unit": "orders",
                    "formula": "SUM(ad_performance.conversions)",
                }
            )
            results.append(
                {
                    "date": day,
                    "code": "ad_impressions",
                    "name": "Ad Impressions",
                    "value": Decimal(impressions),
                    "unit": "impressions",
                    "formula": "SUM(ad_performance.impressions)",
                }
            )
            results.append(
                {
                    "date": day,
                    "code": "ad_clicks",
                    "name": "Ad Clicks",
                    "value": Decimal(clicks),
                    "unit": "clicks",
                    "formula": "SUM(ad_performance.clicks)",
                }
            )
        return results

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _persist_kpis(
        self,
        store_id: str,
        organization_id: str,
        business_id: str,
        rows: List[Dict[str, Any]],
    ) -> None:
        """Upsert KPI rows. Existing rows for (store,date,code) are replaced."""
        dates = {r["date"] for r in rows}
        date_objs = []
        for d in dates:
            if isinstance(d, str):
                date_objs.append(datetime.strptime(d, "%Y-%m-%d").date())
            else:
                date_objs.append(d)

        if date_objs:
            self.session.query(KPI).filter(
                KPI.store_id == store_id,
                KPI.organization_id == organization_id,
                KPI.business_id == business_id,
                KPI.freshness.in_([datetime.combine(d, datetime.min.time()) for d in date_objs]),
            ).delete(synchronize_session=False)

        # Insert new rows
        now = utc_now()
        for row in rows:
            d = row["date"]
            if isinstance(d, str):
                d = datetime.strptime(d, "%Y-%m-%d").date()
            kpi = KPI(
                id=new_uuid(),
                code=row["code"],
                name=row["name"],
                description=row.get("formula"),
                formula=row.get("formula"),
                unit=row.get("unit"),
                value=_round2(row["value"]),
                confidence=Decimal("1.0"),
                freshness=datetime.combine(d, datetime.min.time()),
                marketplace_metadata={"date": d.isoformat()},
                organization_id=organization_id,
                business_id=business_id,
                store_id=store_id,
                created_at=now,
                updated_at=now,
            )
            self.session.add(kpi)
            history = KPIHistory(
                id=new_uuid(),
                kpi_id=kpi.id,
                value=kpi.value,
                confidence=kpi.confidence,
                recorded_at=now,
                organization_id=organization_id,
                business_id=business_id,
                store_id=store_id,
                created_at=now,
                updated_at=now,
            )
            self.session.add(history)
        self.session.commit()

    # ------------------------------------------------------------------
    # Commerce State
    # ------------------------------------------------------------------

    def _build_commerce_state(
        self,
        store_id: str,
        organization_id: str,
        business_id: str,
        start: datetime,
        end: datetime,
    ) -> Dict[str, Any]:
        now = utc_now()
        checkpoints = (
            self.session.query(SyncCheckpoint)
            .filter_by(store_id=store_id)
            .all()
        )
        sources_fresh = []
        sources_stale = []
        last_sync = {}
        for cp in checkpoints:
            entity = cp.entity_type
            ts = cp.last_successful_sync_at
            if ts:
                # Normalize to UTC whether the DB stored naive or aware datetimes.
                ts_utc = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
                hours = (now - ts_utc).total_seconds() / 3600
                is_fresh = hours < FRESHNESS_HOURS_THRESHOLD
                (sources_fresh if is_fresh else sources_stale).append(entity)
                last_sync[entity] = {
                    "at": ts_utc.isoformat(),
                    "hours_ago": round(hours, 2),
                    "fresh": is_fresh,
                }

        # Data quality: count open data quality events
        open_events = (
            self.session.query(DataQualityEvent)
            .filter(
                DataQualityEvent.store_id == store_id,
                DataQualityEvent.resolved_at.is_(None),
            )
            .all()
        )
        critical_events = [e for e in open_events if e.severity in ("critical", "high")]
        data_quality_score = Decimal("1.0") if not critical_events else Decimal("0.7")

        # Summary numbers from KPIs for the requested range
        summary = self._summarize_kpis(store_id, start, end)

        alerts = []
        if sources_stale:
            alerts.append(
                {
                    "type": "stale_sources",
                    "entities": sources_stale,
                    "severity": "warning",
                }
            )
        if critical_events:
            alerts.append(
                {
                    "type": "data_quality",
                    "count": len(critical_events),
                    "severity": "critical" if any(e.severity == "critical" for e in critical_events) else "high",
                }
            )

        state_id = new_uuid()
        return {
            "id": state_id,
            "version": "1",
            "valid_until": now + timedelta(hours=1),
            "data_quality_score": data_quality_score,
            "confidence_level": "high" if data_quality_score == Decimal("1.0") else "medium",
            "sources_fresh": sources_fresh,
            "sources_stale": sources_stale,
            "summary": summary,
            "alerts": alerts,
            "risks": [],
            "opportunities": [],
            "anomalies": [],
            "todays_focus": {
                "message": "Review stale sources" if sources_stale else "All sources fresh",
                "entities": sources_stale,
            },
            "last_sync": last_sync,
            "data_quality": {
                "score": float(data_quality_score),
                "open_events": len(open_events),
                "critical_events": len(critical_events),
            },
            "marketplace_metadata": None,
            "organization_id": organization_id,
            "business_id": business_id,
            "store_id": store_id,
            "created_at": now,
            "updated_at": now,
        }

    def _summarize_kpis(
        self, store_id: str, start: datetime, end: datetime
    ) -> Dict[str, Any]:
        kpis = (
            self.session.query(KPI)
            .filter(
                KPI.store_id == store_id,
                KPI.freshness >= start,
                KPI.freshness <= end,
            )
            .all()
        )
        by_code: Dict[str, Decimal] = {}
        for kpi in kpis:
            by_code[kpi.code] = by_code.get(kpi.code, Decimal("0")) + kpi.value

        # ROAS/CTR are averages, not sums
        roas_days = [k for k in kpis if k.code == "roas"]
        ctr_days = [k for k in kpis if k.code == "ctr"]
        avg_roas = (
            _round2(Decimal(str(sum(k.value for k in roas_days) / len(roas_days)))) if roas_days else Decimal("0")
        )
        avg_ctr = (
            _round2(Decimal(str(sum(k.value for k in ctr_days) / len(ctr_days)))) if ctr_days else Decimal("0")
        )

        # AOV must be recomputed from totals, not summed across days.
        total_gross_sales = by_code.get("gross_sales", Decimal("0"))
        total_order_count = by_code.get("order_count", Decimal("0"))
        aov = _round2(total_gross_sales / total_order_count) if total_order_count else Decimal("0")

        return {
            "gross_sales": float(total_gross_sales),
            "net_sales": float(by_code.get("net_sales", Decimal("0"))),
            "order_count": int(total_order_count),
            "shopee_fees": float(by_code.get("shopee_fees", Decimal("0"))),
            "gross_profit": float(by_code.get("gross_profit", Decimal("0"))),
            "ad_spend": float(by_code.get("ad_spend", Decimal("0"))),
            "ad_revenue": float(by_code.get("ad_revenue", Decimal("0"))),
            "roas": float(_round2(avg_roas)),
            "ctr": float(_round2(avg_ctr)),
            "aov": float(aov),
        }

    def _persist_commerce_state(self, state: Dict[str, Any]) -> None:
        record = CommerceState(
            id=state["id"],
            version=state["version"],
            valid_until=state["valid_until"],
            data_quality_score=state["data_quality_score"],
            confidence_level=state["confidence_level"],
            sources_fresh=state["sources_fresh"],
            sources_stale=state["sources_stale"],
            summary=state["summary"],
            alerts=state["alerts"],
            risks=state["risks"],
            opportunities=state["opportunities"],
            anomalies=state["anomalies"],
            todays_focus=state["todays_focus"],
            last_sync=state["last_sync"],
            data_quality=state["data_quality"],
            marketplace_metadata=state["marketplace_metadata"],
            organization_id=state["organization_id"],
            business_id=state["business_id"],
            store_id=state["store_id"],
            created_at=state["created_at"],
            updated_at=state["updated_at"],
        )
        self.session.add(record)
        self.session.commit()

    # ------------------------------------------------------------------
    # Read helpers used by DashboardQueryService
    # ------------------------------------------------------------------

    @staticmethod
    def aggregate_kpis(
        kpis: List[KPI],
        codes: List[str],
        average_codes: Optional[List[str]] = None,
    ) -> Dict[str, Decimal]:
        """Sum KPI values by code; average for codes in average_codes."""
        average_codes = average_codes or []
        by_code: Dict[str, List[Decimal]] = {c: [] for c in codes}
        for kpi in kpis:
            if kpi.code in by_code:
                by_code[kpi.code].append(kpi.value)
        result: Dict[str, Decimal] = {}
        for code in codes:
            values = by_code[code]
            if not values:
                result[code] = Decimal("0")
            elif code in average_codes:
                result[code] = _round2(sum(values) / len(values))
            else:
                result[code] = _round2(sum(values))
        return result

    @staticmethod
    def latest_commerce_state(
        session: Session, store_id: str
    ) -> Optional[CommerceState]:
        return (
            session.query(CommerceState)
            .filter_by(store_id=store_id)
            .order_by(CommerceState.created_at.desc())
            .first()
        )
