"""Add viewport column and index to findings table.

Revision ID: 004_add_finding_viewport
Revises: 003_add_run_user_id
Create Date: 2026-11-13 22:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004_add_finding_viewport'
down_revision: Union[str, None] = '003_add_run_user_id'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add nullable viewport column to findings table with default 'desktop' and index
    with op.batch_alter_table('findings') as batch_op:
        batch_op.add_column(
            sa.Column('viewport', sa.String(length=32), server_default='desktop', nullable=True)
        )
        batch_op.create_index(op.f('ix_findings_viewport'), ['viewport'], unique=False)


def downgrade() -> None:
    # Drop index and viewport column from findings table
    with op.batch_alter_table('findings') as batch_op:
        batch_op.drop_index(op.f('ix_findings_viewport'))
        batch_op.drop_column('viewport')
