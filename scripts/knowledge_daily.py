"""Generate daily COO brief note.

Usage:
    python scripts/knowledge_daily.py [--date YYYY-MM-DD] [--no-persist]
"""
from __future__ import annotations


import argparse
import sys
from datetime import date, datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from commerceos.config.settings import get_settings
from commerceos.dashboard.query_service import DashboardQueryService
from commerceos.decision.dashboard import DecisionDashboard
from commerceos.events.dashboard import EventsDashboard
from commerceos.execution.dashboard import ExecutionDashboard
from commerceos.intelligence.dashboard import IntelligenceDashboard
from commerceos.knowledge.dashboard import KnowledgeDashboard
from commerceos.knowledge.reporters.coo_brief_generator import KnowledgeReporter, concise_daily_summary
from commerceos.knowledge.sqlalchemy_repositories import SQLAlchemyKnowledgeUnitOfWork
from commerceos.monitoring.dashboard import MonitoringDashboard
from commerceos.platform.database.connection import get_session


def main():
    parser = argparse.ArgumentParser(description="Generate daily COO brief")
    parser.add_argument("--date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--no-persist", action="store_true", help="Write file but do not persist metadata")
    args = parser.parse_args()

    settings = get_settings()
    session = get_session(settings.database_url)

    qs = DashboardQueryService(session=session, database_url=settings.database_url)
    monitoring = MonitoringDashboard.__new__(MonitoringDashboard)
    monitoring.uow = None  # type: ignore
    intelligence = IntelligenceDashboard.__new__(IntelligenceDashboard)
    intelligence.uow = None  # type: ignore
    decisions = DecisionDashboard.__new__(DecisionDashboard)
    decisions.uow = None  # type: ignore
    executions = ExecutionDashboard.__new__(ExecutionDashboard)
    executions.uow = None  # type: ignore
    events = EventsDashboard.__new__(EventsDashboard)
    events.uow = None  # type: ignore

    knowledge_uow = SQLAlchemyKnowledgeUnitOfWork(session)
    knowledge_dashboard = KnowledgeDashboard(knowledge_uow.notes(), vault_dir=settings.obsidian_vault_path)

    reporter = KnowledgeReporter(
        vault_dir=settings.obsidian_vault_path,
        query_service=qs,
        monitoring=monitoring,
        intelligence=intelligence,
        decisions=decisions,
        executions=executions,
        events=events,
        knowledge_dashboard=knowledge_dashboard,
    )

    result = reporter.generate_daily(args.date, persist=not args.no_persist)
    print(f"Daily note written: {result['path']}")
    print(concise_daily_summary(result["memory"]))

    if not args.no_persist:
        knowledge_uow.commit()


if __name__ == "__main__":
    main()
