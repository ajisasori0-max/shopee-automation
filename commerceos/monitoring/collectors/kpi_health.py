"""KPI engine health collector.

Checks last KPI refresh and missing KPIs for a store.
"""
from commerceos.shared.value_objects.primitives import utc_now

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from commerceos.commerce.models import KPI, CommerceState
from commerceos.monitoring.constants import Component, HealthStatus, Severity
from commerceos.monitoring.evaluators.freshness import hours_since
from commerceos.monitoring.evaluators.severity import severity_from_hours
from commerceos.monitoring.models import HealthCheck


def collect_kpi_health(
    session: Session,
    store_id: Optional[str] = None,
    now: Optional[datetime] = None,
) -> List[HealthCheck]:
    """Collect KPI engine health checks for a store."""
    now = now or utc_now()
    checks: List[HealthCheck] = []

    # Use updated_at (refresh timestamp) to determine if KPIs were recently refreshed.
    latest_kpi = (
        session.query(KPI)
        .filter_by(store_id=store_id)
        .order_by(KPI.updated_at.desc())
        .first()
    )
    h = hours_since(latest_kpi.updated_at if latest_kpi else None, now)
    status = HealthStatus.HEALTHY
    if h is None:
        status = HealthStatus.UNHEALTHY
    elif h >= 24:
        status = HealthStatus.UNHEALTHY
    elif h >= 2:
        status = HealthStatus.DEGRADED

    checks.append(
        HealthCheck(
            component=Component.KPI_ENGINE.value,
            component_instance=store_id,
            check_type="kpi_refresh",
            status=status.value,
            severity=severity_from_hours(latest_kpi.updated_at if latest_kpi else None, 24, 2, now).value,
            message=f"Latest KPI refresh {h:.1f} hours ago" if h is not None else "No KPIs found",
            checked_at=now,
            metadata_={
                "store_id": store_id,
                "latest_freshness": latest_kpi.updated_at.isoformat() if latest_kpi else None,
                "hours_since": h,
            },
        )
    )

    # Missing core KPIs for the latest data date. If the KPI engine refreshed
    # recently, missing codes are a data/business gap (not a system failure).
    core_codes = [
        "gross_sales",
        "net_sales",
        "order_count",
        "shopee_fees",
        "gross_profit",
        "ad_spend",
        "ad_revenue",
        "roas",
    ]
    latest_freshness = (
        session.query(func.max(KPI.freshness))
        .filter_by(store_id=store_id)
        .scalar()
    )
    recent_kpis = []
    if latest_freshness:
        recent_kpis = (
            session.query(KPI)
            .filter(
                KPI.store_id == store_id,
                KPI.freshness == latest_freshness,
            )
            .all()
        )
    present_codes = {k.code for k in recent_kpis}
    missing_codes = [c for c in core_codes if c not in present_codes]
    # If KPIs were refreshed recently, missing metrics are data gaps, not errors.
    is_recent_refresh = h is not None and h < 24
    checks.append(
        HealthCheck(
            component=Component.KPI_ENGINE.value,
            component_instance=store_id,
            check_type="missing_kpis",
            status=HealthStatus.HEALTHY.value if (not missing_codes or is_recent_refresh) else HealthStatus.DEGRADED.value,
            severity=Severity.INFO.value if (not missing_codes or is_recent_refresh) else Severity.WARNING.value,
            message=f"Missing {len(missing_codes)} core KPIs for latest data date: {missing_codes}" if missing_codes else "All core KPIs present for latest data date",
            checked_at=now,
            metadata_={
                "store_id": store_id,
                "latest_data_date": latest_freshness.isoformat() if latest_freshness else None,
                "missing_codes": missing_codes,
                "present_count": len(present_codes),
            },
        )
    )

    return checks
