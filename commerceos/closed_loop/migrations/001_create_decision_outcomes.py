"""Migration script for the decision_outcomes table.

Run manually to add the table to an existing database. This project does not use
Alembic, so migrations are applied as standalone SQL scripts.
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from commerceos.closed_loop.models import DecisionOutcome  # noqa: F401 — registers table metadata
from commerceos.config.settings import get_settings
from commerceos.platform.database.connection import create_all, get_engine


def upgrade():
    """Create the decision_outcomes table."""
    settings = get_settings()
    create_all(settings.database_url)


def downgrade():
    """Drop the decision_outcomes table."""
    settings = get_settings()
    engine = get_engine(settings.database_url)
    with engine.connect() as conn:
        conn.execute("DROP TABLE IF EXISTS decision_outcomes")


if __name__ == "__main__":
    upgrade()
    print("decision_outcomes table created.")
