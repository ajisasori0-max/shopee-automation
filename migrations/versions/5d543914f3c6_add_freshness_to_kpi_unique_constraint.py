"""add freshness to kpi unique constraint

Revision ID: 5d543914f3c6
Revises: e467e0be346a
Create Date: 2026-07-23 19:22:18.731243

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5d543914f3c6'
down_revision: Union[str, Sequence[str], None] = 'e467e0be346a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('kpis', schema=None) as batch_op:
        batch_op.drop_constraint('uq_kpi_code', type_='unique')
        batch_op.create_unique_constraint('uq_kpi_code', ['organization_id', 'business_id', 'store_id', 'code', 'freshness'])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('kpis', schema=None) as batch_op:
        batch_op.drop_constraint('uq_kpi_code', type_='unique')
        batch_op.create_unique_constraint('uq_kpi_code', ['organization_id', 'business_id', 'store_id', 'code'])

