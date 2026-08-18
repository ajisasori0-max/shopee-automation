"""Reporting consolidation helpers.

Routes consumers to the canonical reporting path. Legacy reporters remain in
place for compatibility; new code should call the knowledge layer.
"""
from __future__ import annotations


from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy.exc import OperationalError

from commerceos.config.settings import Settings, get_settings
from commerceos.knowledge.dashboard import KnowledgeDashboard
from commerceos.knowledge.sqlalchemy_repositories import SQLAlchemyKnowledgeUnitOfWork
from commerceos.platform.database.connection import get_session


def get_latest_canonical_report(
    note_type: str = "daily",
    settings: Optional[Settings] = None,
) -> Optional[Dict[str, Any]]:
    """Return the latest canonical report metadata from the Knowledge layer.

    Consumers: Telegram scripts, dashboard, OAT verification. Returns None if the
    knowledge table is missing or empty.
    """
    settings = settings or get_settings()
    session = get_session(settings.database_url)
    try:
        uow = SQLAlchemyKnowledgeUnitOfWork(session)
        dashboard = KnowledgeDashboard(uow.notes(), vault_dir=settings.obsidian_vault_path)
        return dashboard.latest_summary(note_type)
    except OperationalError:
        return None
    finally:
        session.close()


def get_report_content(note_id: str, settings: Optional[Settings] = None) -> Optional[Dict[str, Any]]:
    """Load the full Markdown content of a canonical report."""
    settings = settings or get_settings()
    session = get_session(settings.database_url)
    try:
        uow = SQLAlchemyKnowledgeUnitOfWork(session)
        dashboard = KnowledgeDashboard(uow.notes(), vault_dir=settings.obsidian_vault_path)
        return dashboard.read_note(note_id)
    except OperationalError:
        return None
    finally:
        session.close()
