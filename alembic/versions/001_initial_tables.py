"""Create initial tables for runs, findings, artifacts, and repair proposals.

Revision ID: 001_initial_tables
Revises: 
Create Date: 2026-11-01 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial_tables'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Inspection Runs Table
    op.create_table(
        'runs',
        sa.Column('run_id', sa.String(length=128), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='queued', nullable=False),
        sa.Column('created_at', sa.String(length=64), nullable=False),
        sa.Column('completed_at', sa.String(length=64), nullable=True),
        sa.Column('message', sa.Text(), server_default='Run created successfully and queued for inspection.', nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('run_id')
    )
    op.create_index(op.f('ix_runs_run_id'), 'runs', ['run_id'], unique=False)
    op.create_index(op.f('ix_runs_status'), 'runs', ['status'], unique=False)
    op.create_index(op.f('ix_runs_created_at'), 'runs', ['created_at'], unique=False)

    # 2. Defect Findings Table
    op.create_table(
        'findings',
        sa.Column('finding_id', sa.String(length=128), nullable=False),
        sa.Column('run_id', sa.String(length=128), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=False),
        sa.Column('severity', sa.String(length=32), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('selector', sa.Text(), nullable=True),
        sa.Column('screenshot_path', sa.Text(), nullable=True),
        sa.Column('dom_snapshot_path', sa.Text(), nullable=True),
        sa.Column('source', sa.String(length=32), server_default='mock', nullable=False),
        sa.Column('created_at', sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['runs.run_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('finding_id')
    )
    op.create_index(op.f('ix_findings_finding_id'), 'findings', ['finding_id'], unique=False)
    op.create_index(op.f('ix_findings_run_id'), 'findings', ['run_id'], unique=False)
    op.create_index(op.f('ix_findings_category'), 'findings', ['category'], unique=False)
    op.create_index(op.f('ix_findings_severity'), 'findings', ['severity'], unique=False)

    # 3. Artifacts Table
    op.create_table(
        'artifacts',
        sa.Column('artifact_id', sa.String(length=128), nullable=False),
        sa.Column('run_id', sa.String(length=128), nullable=False),
        sa.Column('artifact_type', sa.String(length=64), nullable=False),
        sa.Column('storage_path', sa.Text(), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('content_type', sa.String(length=64), nullable=True),
        sa.Column('captured_at', sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['runs.run_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('artifact_id')
    )
    op.create_index(op.f('ix_artifacts_artifact_id'), 'artifacts', ['artifact_id'], unique=False)
    op.create_index(op.f('ix_artifacts_run_id'), 'artifacts', ['run_id'], unique=False)
    op.create_index(op.f('ix_artifacts_artifact_type'), 'artifacts', ['artifact_type'], unique=False)

    # 4. Repair Proposals Table
    op.create_table(
        'repair_proposals',
        sa.Column('proposal_id', sa.String(length=128), nullable=False),
        sa.Column('run_id', sa.String(length=128), nullable=False),
        sa.Column('finding_id', sa.String(length=128), nullable=True),
        sa.Column('proposed_change', sa.Text(), nullable=False),
        sa.Column('approval_status', sa.String(length=32), server_default='pending', nullable=False),
        sa.Column('execution_status', sa.String(length=32), server_default='unapplied', nullable=False),
        sa.Column('verification_status', sa.String(length=32), server_default='unverified', nullable=False),
        sa.Column('github_pr_url', sa.Text(), nullable=True),
        sa.Column('github_pr_number', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.String(length=64), nullable=False),
        sa.Column('updated_at', sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(['finding_id'], ['findings.finding_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['run_id'], ['runs.run_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('proposal_id')
    )
    op.create_index(op.f('ix_repair_proposals_proposal_id'), 'repair_proposals', ['proposal_id'], unique=False)
    op.create_index(op.f('ix_repair_proposals_run_id'), 'repair_proposals', ['run_id'], unique=False)
    op.create_index(op.f('ix_repair_proposals_finding_id'), 'repair_proposals', ['finding_id'], unique=False)
    op.create_index(op.f('ix_repair_proposals_approval_status'), 'repair_proposals', ['approval_status'], unique=False)


def downgrade() -> None:
    op.drop_table('repair_proposals')
    op.drop_table('artifacts')
    op.drop_table('findings')
    op.drop_table('runs')
