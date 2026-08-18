"""Database migration script for the knowledge_notes table.

Run manually to add the table to an existing database. This project does not use
Alembic, so migrations are applied as standalone SQL scripts.
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from commerceos.config.settings import get_settings
from commerceos.knowledge.models import KnowledgeNote  # noqa: F401 — registers table metadata
from commerceos.platform.database.connection import get_engine, create_all


def upgrade():
    """Create the knowledge_notes table."""
    settings = get_settings()
    create_all(settings.database_url)


def downgrade():
    """Drop the knowledge_notes table."""
    settings = get_settings()
    engine = get_engine(settings.database_url)
    with engine.connect() as conn:
        conn.execute("DROP TABLE IF EXISTS knowledge_notes")


if __name__ == "__main__":
    upgrade()
    print("knowledge_notes table created.")
