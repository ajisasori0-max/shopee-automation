"""Send evening COO review to Telegram."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from commerceos.config.settings import get_settings
from commerceos.dashboard.query_service import DashboardQueryService
from commerceos.decision.dashboard import DecisionDashboard
from commerceos.decision.sqlalchemy_repositories import SQLAlchemyDecisionUnitOfWork
from commerceos.execution.dashboard import ExecutionDashboard
from commerceos.execution.sqlalchemy_repositories import SQLAlchemyExecutionUnitOfWork
from commerceos.monitoring.dashboard import MonitoringDashboard
from commerceos.monitoring.sqlalchemy_repositories import SQLAlchemyMonitoringUnitOfWork
from commerceos.platform.database.connection import get_session
from commerceos.telegram.notifier import COOReporter
from commerceos.shared.value_objects.primitives import utc_now

STORE_ID = "store-ppm-001"


def main():
    settings = get_settings()
    session = get_session(settings.database_url)
    try:
        qs = DashboardQueryService(session=session, database_url=settings.database_url)
        today = utc_now().replace(hour=0, minute=0, second=0, microsecond=0)
        pl = qs.get_pl_summary(STORE_ID, today, today + timedelta(days=1, seconds=-1))
        wins = [f"Revenue: Rp {pl.get('net_sales', 0):,.0f}"] if pl.get('net_sales', 0) else []

        monitoring_uow = SQLAlchemyMonitoringUnitOfWork(session)
        monitoring = MonitoringDashboard(monitoring_uow)
        alerts = monitoring.get_open_alerts() or []
        issues = [f"{a.get('severity', '—')} — {a.get('message', '—')}" for a in alerts[:5]]

        execution_uow = SQLAlchemyExecutionUnitOfWork(session)
        execution_dashboard = ExecutionDashboard(execution_uow)
        recent = execution_dashboard.get_recent_executions(hours=24, limit=10) or []
        completed = [e.get("action_type", "action") for e in recent if e.get("status") in ("completed", "success")]
        unresolved = [e.get("action_type", "action") for e in recent if e.get("status") in ("failed", "partial")]

        decision_uow = SQLAlchemyDecisionUnitOfWork(session)
        decisions = DecisionDashboard(decision_uow)
        open_decisions = decisions.get_open_decisions(limit=10) or []
        unresolved += [f"Decision: {d.get('title', '—')}" for d in open_decisions]

        reporter = COOReporter(settings=settings)
        delivery = reporter.evening_review(
            wins=wins,
            issues=issues,
            completed_actions=completed,
            unresolved_items=unresolved,
        )
        print(delivery.to_dict())
    finally:
        session.close()


if __name__ == "__main__":
    main()
