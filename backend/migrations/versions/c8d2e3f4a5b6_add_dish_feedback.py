"""add dish feedback

Revision ID: c8d2e3f4a5b6
Revises: b7f1c2d3e4a5
Create Date: 2026-10-31 03:40:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c8d2e3f4a5b6'
down_revision: Union[str, None] = 'b7f1c2d3e4a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'dish_feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('dish_id', sa.Integer(), nullable=False),
        sa.Column('log_id', sa.Integer(), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['dish_id'], ['dishes_and_recipes.id']),
        sa.ForeignKeyConstraint(['log_id'], ['eating_logs.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_dish_feedback_user_id', 'dish_feedback', ['user_id'])
    op.create_index('ix_dish_feedback_dish_id', 'dish_feedback', ['dish_id'])
    op.create_index('ix_dish_feedback_log_id', 'dish_feedback', ['log_id'])
    op.create_index('ix_dish_feedback_created_at', 'dish_feedback', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_dish_feedback_created_at', table_name='dish_feedback')
    op.drop_index('ix_dish_feedback_log_id', table_name='dish_feedback')
    op.drop_index('ix_dish_feedback_dish_id', table_name='dish_feedback')
    op.drop_index('ix_dish_feedback_user_id', table_name='dish_feedback')
    op.drop_table('dish_feedback')
