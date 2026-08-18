"""Generate weekly COO brief note and apply retention.

Usage:
    python scripts/knowledge_weekly.py [--week-date YYYY-MM-DD] [--no-retention]
"""
from __future__ import annotations


import argparse
import sys
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from commerceos.config.settings import get_settings
from commerceos.knowledge.reporters.coo_brief_generator import KnowledgeReporter
from commerceos.knowledge.sqlalchemy_repositories import SQLAlchemyKnowledgeUnitOfWork
from commerceos.platform.database.connection import get_session


def main():
    parser = argparse.ArgumentParser(description="Generate weekly COO brief")
    parser.add_argument("--week-date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--no-retention", action="store_true", help="Skip archiving old dailies")
    args = parser.parse_args()

    settings = get_settings()
    session = get_session(settings.database_url)
    knowledge_uow = SQLAlchemyKnowledgeUnitOfWork(session)

    reporter = KnowledgeReporter(
        vault_dir=settings.obsidian_vault_path,
        knowledge_dashboard=None,  # Will default; metadata persistence disabled in this standalone script unless updated.
    )
    result = reporter.generate_weekly(args.week_date, persist=False)
    print(f"Weekly note written: {result['path']}")

    if not args.no_retention:
        retention_result = reporter.apply_retention()
        print(f"Retention archived: {retention_result}")


if __name__ == "__main__":
    main()
