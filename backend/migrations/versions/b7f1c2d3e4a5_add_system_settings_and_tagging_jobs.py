"""add system settings and tagging jobs

Revision ID: b7f1c2d3e4a5
Revises: 0a755691cec1
Create Date: 2026-10-31 01:45:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b7f1c2d3e4a5'
down_revision: Union[str, None] = '0a755691cec1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'system_settings',
        sa.Column('key', sa.String(length=64), nullable=False),
        sa.Column('value', sa.JSON(), nullable=False),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id']),
        sa.PrimaryKeyConstraint('key'),
    )
    op.create_table(
        'tagging_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('total', sa.Integer(), nullable=False),
        sa.Column('done', sa.Integer(), nullable=False),
        sa.Column('failed', sa.Integer(), nullable=False),
        sa.Column('dish_ids', sa.JSON(), nullable=False),
        sa.Column('message', sa.String(length=255), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_tagging_jobs_status', 'tagging_jobs', ['status'])
    op.create_index('ix_tagging_jobs_created_at', 'tagging_jobs', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_tagging_jobs_created_at', table_name='tagging_jobs')
    op.drop_index('ix_tagging_jobs_status', table_name='tagging_jobs')
    op.drop_table('tagging_jobs')
    op.drop_table('system_settings')
