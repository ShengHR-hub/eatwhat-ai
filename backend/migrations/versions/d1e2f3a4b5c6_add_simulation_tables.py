"""add simulation experiment tables

Revision ID: d1e2f3a4b5c6
Revises: c8d2e3f4a5b6
Create Date: 2026-10-31 20:40:00

G3 仿真数据单独落表，不与真实 eating_logs / room_votes 混用。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, None] = 'c8d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'simulation_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('seed', sa.Integer(), nullable=False),
        sa.Column('personas', sa.Integer(), nullable=False),
        sa.Column('days', sa.Integer(), nullable=False),
        sa.Column('meals_per_day', sa.Integer(), nullable=False),
        sa.Column('rooms_count', sa.Integer(), nullable=False),
        sa.Column('members_per_room', sa.Integer(), nullable=False),
        sa.Column('lambda_decay', sa.Float(), nullable=True),
        sa.Column('omega_group', sa.Float(), nullable=True),
        sa.Column('generated_at', sa.DateTime(), nullable=True),
        sa.Column('imported_at', sa.DateTime(), nullable=False),
        sa.Column('source_dir', sa.String(length=255), nullable=False),
        sa.Column('metrics', sa.JSON(), nullable=False),
        sa.Column('meal_rows', sa.Integer(), nullable=False),
        sa.Column('room_rows', sa.Integer(), nullable=False),
        sa.Column('vote_rows', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_index('ix_simulation_runs_name', 'simulation_runs', ['name'])
    op.create_index('ix_simulation_runs_imported_at', 'simulation_runs', ['imported_at'])

    op.create_table(
        'simulation_meal_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('arm', sa.String(length=16), nullable=False),
        sa.Column('persona_id', sa.Integer(), nullable=False),
        sa.Column('day', sa.Integer(), nullable=False),
        sa.Column('meal', sa.Integer(), nullable=False),
        sa.Column('mode_type', sa.String(length=16), nullable=False),
        sa.Column('dish_id', sa.Integer(), nullable=False),
        sa.Column('dish_name', sa.String(length=128), nullable=False),
        sa.Column('cuisine_type', sa.String(length=64), nullable=False),
        sa.Column('total_score', sa.Float(), nullable=False),
        sa.Column('decay_weight', sa.Float(), nullable=False),
        sa.Column('duplicated', sa.Boolean(), nullable=False),
        sa.Column('candidate_count', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['simulation_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'run_id', 'arm', 'persona_id', 'day', 'meal', name='uq_sim_meal'
        ),
    )
    op.create_index('ix_simulation_meal_logs_run_id', 'simulation_meal_logs', ['run_id'])
    op.create_index('ix_sim_meal_run_arm', 'simulation_meal_logs', ['run_id', 'arm'])
    op.create_index('ix_sim_meal_run_day', 'simulation_meal_logs', ['run_id', 'day'])

    op.create_table(
        'simulation_rooms',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('room_code', sa.String(length=10), nullable=False),
        sa.Column('mode_type', sa.String(length=16), nullable=False),
        sa.Column('member_user_ids', sa.JSON(), nullable=False),
        sa.Column('candidate_dish_ids', sa.JSON(), nullable=False),
        sa.Column('winner_dish_id', sa.Integer(), nullable=True),
        sa.Column('votes_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['simulation_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('run_id', 'room_code', name='uq_sim_room'),
    )
    op.create_index('ix_simulation_rooms_run_id', 'simulation_rooms', ['run_id'])
    op.create_index('ix_sim_room_run_mode', 'simulation_rooms', ['run_id', 'mode_type'])

    op.create_table(
        'simulation_room_votes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('room_code', sa.String(length=10), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('dish_id', sa.Integer(), nullable=False),
        sa.Column('vote_type', sa.String(length=16), nullable=False),
        sa.Column('voted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['simulation_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'run_id', 'room_code', 'user_id', 'dish_id', name='uq_sim_vote'
        ),
    )
    op.create_index('ix_simulation_room_votes_run_id', 'simulation_room_votes', ['run_id'])
    op.create_index('ix_sim_vote_run_room', 'simulation_room_votes', ['run_id', 'room_code'])
    op.create_index('ix_sim_vote_run_type', 'simulation_room_votes', ['run_id', 'vote_type'])

    op.create_table(
        'simulation_group_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('strategy', sa.String(length=64), nullable=False),
        sa.Column('avg_score', sa.Float(), nullable=False),
        sa.Column('least_misery_score', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['simulation_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('run_id', 'strategy', name='uq_sim_group'),
    )
    op.create_index('ix_simulation_group_results_run_id', 'simulation_group_results', ['run_id'])


def downgrade() -> None:
    op.drop_index('ix_simulation_group_results_run_id', table_name='simulation_group_results')
    op.drop_table('simulation_group_results')
    op.drop_index('ix_sim_vote_run_type', table_name='simulation_room_votes')
    op.drop_index('ix_sim_vote_run_room', table_name='simulation_room_votes')
    op.drop_index('ix_simulation_room_votes_run_id', table_name='simulation_room_votes')
    op.drop_table('simulation_room_votes')
    op.drop_index('ix_sim_room_run_mode', table_name='simulation_rooms')
    op.drop_index('ix_simulation_rooms_run_id', table_name='simulation_rooms')
    op.drop_table('simulation_rooms')
    op.drop_index('ix_sim_meal_run_day', table_name='simulation_meal_logs')
    op.drop_index('ix_sim_meal_run_arm', table_name='simulation_meal_logs')
    op.drop_index('ix_simulation_meal_logs_run_id', table_name='simulation_meal_logs')
    op.drop_table('simulation_meal_logs')
    op.drop_index('ix_simulation_runs_imported_at', table_name='simulation_runs')
    op.drop_index('ix_simulation_runs_name', table_name='simulation_runs')
    op.drop_table('simulation_runs')
