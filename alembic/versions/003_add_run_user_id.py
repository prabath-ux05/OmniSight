"""Add user_id column and foreign key to runs table.

Revision ID: 003_add_run_user_id
Revises: 002_add_auth_tables
Create Date: 2026-11-13 19:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_add_run_user_id'
down_revision: Union[str, None] = '002_add_auth_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add nullable user_id column to runs table
    op.add_column(
        'runs',
        sa.Column('user_id', sa.String(length=36), nullable=True),
    )
    op.create_index(op.f('ix_runs_user_id'), 'runs', ['user_id'], unique=False)
    op.create_foreign_key(
        'fk_runs_user_id_users',
        'runs',
        'users',
        ['user_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_runs_user_id_users', 'runs', type_='foreignkey')
    op.drop_index(op.f('ix_runs_user_id'), table_name='runs')
    op.drop_column('runs', 'user_id')
