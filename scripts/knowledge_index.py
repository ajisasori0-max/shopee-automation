"""Regenerate the knowledge vault index.

Usage:
    python scripts/knowledge_index.py
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from commerceos.config.settings import get_settings
from commerceos.knowledge.index import KnowledgeIndex
from commerceos.knowledge.sqlalchemy_repositories import SQLAlchemyKnowledgeUnitOfWork
from commerceos.platform.database.connection import get_session


def main():
    settings = get_settings()
    session = get_session(settings.database_url)
    uow = SQLAlchemyKnowledgeUnitOfWork(session)
    index = KnowledgeIndex(settings.obsidian_vault_path, repository=uow.notes())
    path = index.generate()
    print(f"Index regenerated: {path}")


if __name__ == "__main__":
    main()
