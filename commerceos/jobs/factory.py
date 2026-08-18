"""Factory for registering default CommerceOS jobs."""


from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from commerceos.config.settings import Settings, get_settings
from commerceos.jobs.handlers import (
    daily_coo_brief,
    knowledge_index_refresh,
    knowledge_retention,
    monthly_executive_review,
    sop_engine_run,
    system_health_check,
    weekly_business_review,
)
from commerceos.jobs.registry import JobRegistry
from commerceos.knowledge.reporters.coo_brief_generator import KnowledgeReporter
from commerceos.monitoring.service import MonitoringService


def register_default_jobs(
    session: Optional[Session] = None,
    settings: Optional[Settings] = None,
    monitoring_service: Optional[MonitoringService] = None,
    knowledge_reporter: Optional[KnowledgeReporter] = None,
) -> JobRegistry:
    """Register the standard CommerceOS operational jobs."""
    registry = JobRegistry()

    registry.register(
        name="daily_coo_brief",
        handler=daily_coo_brief,
        group="knowledge",
        description="Generate daily COO brief and persist metadata.",
        schedule_hint="daily 08:00",
        idempotency_key=lambda: date.today().isoformat(),
    )
    registry.register(
        name="weekly_business_review",
        handler=weekly_business_review,
        group="knowledge",
        description="Generate weekly business review and persist metadata.",
        schedule_hint="monday 08:00",
        idempotency_key=lambda: _week_key(),
    )
    registry.register(
        name="monthly_executive_review",
        handler=monthly_executive_review,
        group="knowledge",
        description="Generate monthly executive review and persist metadata.",
        schedule_hint="first day of month 08:00",
        idempotency_key=lambda: date.today().replace(day=1).isoformat(),
    )
    registry.register(
        name="sop_engine_run",
        handler=sop_engine_run,
        group="operations",
        description="Run deterministic SOP evaluations and create proposed decisions.",
        schedule_hint="daily 08:15",
        idempotency_key=lambda: date.today().isoformat(),
    )
    registry.register(
        name="knowledge_index_refresh",
        handler=knowledge_index_refresh,
        group="knowledge",
        description="Regenerate the knowledge vault index from metadata.",
        schedule_hint="daily 08:30",
    )
    registry.register(
        name="knowledge_retention",
        handler=knowledge_retention,
        group="knowledge",
        description="Archive older daily/weekly/monthly notes.",
        schedule_hint="monday 08:30",
    )
    registry.register(
        name="system_health_check",
        handler=system_health_check,
        group="monitoring",
        description="Collect health checks, evaluate alerts, and generate snapshot.",
        schedule_hint="every 4 hours",
    )
    return registry


def _week_key() -> str:
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    return week_start.isoformat()
