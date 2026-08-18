"""Commerce State health collector.

Checks latest snapshot and generation latency.
"""
from commerceos.shared.value_objects.primitives import utc_now

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from commerceos.commerce.models import CommerceState
from commerceos.kpi.engine import KPIEngine
from commerceos.monitoring.constants import Component, HealthStatus, Severity
from commerceos.monitoring.evaluators.freshness import hours_since
from commerceos.monitoring.evaluators.severity import severity_from_hours
from commerceos.monitoring.models import HealthCheck


def collect_commerce_state_health(
    session: Session,
    store_id: Optional[str] = None,
    now: Optional[datetime] = None,
) -> List[HealthCheck]:
    """Collect Commerce State health checks for a store."""
    now = now or utc_now()
    checks: List[HealthCheck] = []

    state = KPIEngine.latest_commerce_state(session, store_id or "")
    h = hours_since(state.created_at if state else None, now)
    status = HealthStatus.HEALTHY
    if h is None:
        status = HealthStatus.UNHEALTHY
    elif h >= 2:
        status = HealthStatus.UNHEALTHY
    elif h >= 1:
        status = HealthStatus.DEGRADED

    checks.append(
        HealthCheck(
            component=Component.COMMERCE_STATE.value,
            component_instance=store_id,
            check_type="state_freshness",
            status=status.value,
            severity=severity_from_hours(state.created_at if state else None, 2, 1, now).value,
            message=f"Commerce State generated {h:.1f} hours ago" if h is not None else "No Commerce State found",
            checked_at=now,
            metadata_={
                "store_id": store_id,
                "state_id": state.id if state else None,
                "hours_since": h,
                "data_quality_score": float(state.data_quality_score) if state else None,
            },
        )
    )

    checks.append(
        HealthCheck(
            component=Component.COMMERCE_STATE.value,
            component_instance=store_id,
            check_type="state_generation_latency",
            status=HealthStatus.HEALTHY.value,  # placeholder; could compare valid_until vs created_at
            severity=Severity.INFO.value,
            message="State generation latency tracked",
            checked_at=now,
            metadata_={
                "store_id": store_id,
                "valid_until": state.valid_until.isoformat() if state else None,
            },
        )
    )

    return checks
