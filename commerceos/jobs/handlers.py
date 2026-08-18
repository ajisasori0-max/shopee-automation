"""Job handlers for the standard CommerceOS operational cycle."""


from datetime import date
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from commerceos.config.settings import Settings, get_settings
from commerceos.dashboard.query_service import DashboardQueryService
from commerceos.decision.dashboard import DecisionDashboard
from commerceos.events.dashboard import EventsDashboard
from commerceos.execution.dashboard import ExecutionDashboard
from commerceos.intelligence.dashboard import IntelligenceDashboard
from commerceos.knowledge.dashboard import KnowledgeDashboard
from commerceos.knowledge.reporters.coo_brief_generator import KnowledgeReporter
from commerceos.knowledge.sqlalchemy_repositories import SQLAlchemyKnowledgeUnitOfWork
from commerceos.monitoring.dashboard import MonitoringDashboard
from commerceos.monitoring.service import MonitoringService
from commerceos.monitoring.sqlalchemy_repositories import SQLAlchemyMonitoringUnitOfWork


STORE_ID = "store-ppm-001"


def _default_settings(settings: Optional[Settings] = None) -> Settings:
    return settings or get_settings()


def _default_knowledge_reporter(
    session: Session,
    settings: Optional[Settings] = None,
) -> KnowledgeReporter:
    """Build a knowledge reporter wired to the given database session."""
    settings = _default_settings(settings)
    knowledge_uow = SQLAlchemyKnowledgeUnitOfWork(session)
    knowledge_dashboard = KnowledgeDashboard(
        knowledge_uow.notes(),
        vault_dir=settings.obsidian_vault_path,
    )
    query_service = DashboardQueryService(
        session=session,
        database_url=settings.database_url,
    )
    monitoring = MonitoringDashboard(SQLAlchemyMonitoringUnitOfWork(session))
    intelligence = IntelligenceDashboard(None)  # type: ignore
    decisions = DecisionDashboard(None)  # type: ignore
    executions = ExecutionDashboard(None)  # type: ignore
    events = EventsDashboard(None)  # type: ignore
    return KnowledgeReporter(
        vault_dir=settings.obsidian_vault_path,
        query_service=query_service,
        monitoring=monitoring,
        intelligence=intelligence,
        decisions=decisions,
        executions=executions,
        events=events,
        knowledge_dashboard=knowledge_dashboard,
    )


def _default_monitoring_service(
    session: Session,
    settings: Optional[Settings] = None,
) -> MonitoringService:
    settings = _default_settings(settings)
    monitoring_uow = SQLAlchemyMonitoringUnitOfWork(session)
    return MonitoringService(uow=monitoring_uow, session=session)


def daily_coo_brief(session: Session, settings: Optional[Settings] = None) -> Dict[str, Any]:
    """Generate the daily COO brief note and update the index."""
    reporter = _default_knowledge_reporter(session, settings)
    return reporter.generate_daily(date.today(), persist=True)


def weekly_business_review(session: Session, settings: Optional[Settings] = None) -> Dict[str, Any]:
    """Generate the weekly business review note and update the index."""
    reporter = _default_knowledge_reporter(session, settings)
    return reporter.generate_weekly(date.today(), persist=True)


def monthly_executive_review(session: Session, settings: Optional[Settings] = None) -> Dict[str, Any]:
    """Generate the monthly executive review note and update the index."""
    reporter = _default_knowledge_reporter(session, settings)
    return reporter.generate_monthly(date.today(), persist=True)


def knowledge_index_refresh(session: Session, settings: Optional[Settings] = None) -> Dict[str, Any]:
    """Regenerate the knowledge vault index."""
    reporter = _default_knowledge_reporter(session, settings)
    path = reporter.update_index()
    return {"path": str(path)}


def knowledge_retention(session: Session, settings: Optional[Settings] = None) -> Dict[str, Any]:
    """Apply knowledge retention policy (weekly run)."""
    reporter = _default_knowledge_reporter(session, settings)
    return reporter.apply_retention()


def system_health_check(session: Session, settings: Optional[Settings] = None) -> Dict[str, Any]:
    """Collect system health, evaluate alerts, and generate a snapshot."""
    service = _default_monitoring_service(session, settings)
    checks = service.collect_and_persist(store_id=STORE_ID)
    alerts = service.evaluate_alerts(checks)
    snapshot = service.generate_snapshot(checks)
    return {
        "checks_count": len(checks),
        "alerts_count": len(alerts),
        "snapshot_status": snapshot.overall_status if snapshot else "unknown",
    }


def sop_engine_run(session: Session, settings: Optional[Settings] = None) -> Dict[str, Any]:
    """Run the SOP engine and return a summary of applicable SOPs."""
    from commerceos.sop.engine import run_sop_engine

    return run_sop_engine(
        session,
        store_id=STORE_ID,
        persist_decisions=True,
        publish_events=True,
        record_knowledge=True,
        record_executions=True,
    )
