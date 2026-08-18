"""Send morning COO brief to Telegram."""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from commerceos.config.settings import get_settings
from commerceos.dashboard.query_service import DashboardQueryService
from commerceos.decision.dashboard import DecisionDashboard
from commerceos.decision.sqlalchemy_repositories import SQLAlchemyDecisionUnitOfWork
from commerceos.monitoring.dashboard import MonitoringDashboard
from commerceos.monitoring.sqlalchemy_repositories import SQLAlchemyMonitoringUnitOfWork
from commerceos.platform.database.connection import get_session
from commerceos.telegram.notifier import COOReporter

STORE_ID = "store-ppm-001"


def main():
    settings = get_settings()
    session = get_session(settings.database_url)
    try:
        qs = DashboardQueryService(session=session, database_url=settings.database_url)
        business_state = qs.get_commerce_state(STORE_ID) or {}

        monitoring_uow = SQLAlchemyMonitoringUnitOfWork(session)
        monitoring = MonitoringDashboard(monitoring_uow)
        open_alerts = monitoring.get_open_alerts() or []

        decision_uow = SQLAlchemyDecisionUnitOfWork(session)
        decisions = DecisionDashboard(decision_uow)
        open_decisions = decisions.get_open_decisions(limit=10) or []

        reporter = COOReporter(settings=settings)
        delivery = reporter.morning_brief(
            business_state=business_state.get("summary", business_state),
            open_alerts=open_alerts,
            open_decisions=open_decisions,
        )
        print(delivery.to_dict())
    finally:
        session.close()


if __name__ == "__main__":
    main()
