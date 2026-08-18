"""add job execution log table

Revision ID: a1b2c3d4e5f6
Revises: 9c1d2e3f4a5b
Create Date: 2026-07-25 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '9c1d2e3f4a5b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'job_executions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('job_name', sa.String(length=255), nullable=False),
        sa.Column('job_group', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('metadata_', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_job_executions'))
    )
    with op.batch_alter_table('job_executions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_job_executions_job_name'), ['job_name'], unique=False)
        batch_op.create_index('ix_job_executions_name_finished', ['job_name', 'finished_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('job_executions', schema=None) as batch_op:
        batch_op.drop_index('ix_job_executions_name_finished')
        batch_op.drop_index(batch_op.f('ix_job_executions_job_name'))
    op.drop_table('job_executions')
