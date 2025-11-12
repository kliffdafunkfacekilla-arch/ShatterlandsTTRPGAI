"""add combat_encounters and combat_participants tables

Revision ID: d2f1a4b9c8e3
Revises: 0001_create_story_tables
Create Date: 2025-11-12 00:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'd2f1a4b9c8e3'
down_revision = '0001_create_story_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing = inspector.get_table_names()

    if 'combat_encounters' not in existing:
        op.create_table(
            'combat_encounters',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('location_id', sa.Integer(), nullable=True, index=False),
            sa.Column('status', sa.String(), nullable=True),
            sa.Column('turn_order', sa.JSON(), nullable=True),
            sa.Column('current_turn_index', sa.Integer(), nullable=True),
        )
        try:
            op.create_index(op.f('ix_combat_encounters_id'), 'combat_encounters', ['id'], unique=False)
            op.create_index(op.f('ix_combat_encounters_status'), 'combat_encounters', ['status'], unique=False)
        except Exception:
            pass

    if 'combat_participants' not in existing:
        op.create_table(
            'combat_participants',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('combat_id', sa.Integer(), sa.ForeignKey('combat_encounters.id'), nullable=True),
            sa.Column('actor_id', sa.String(), nullable=True),
            sa.Column('actor_type', sa.String(), nullable=True),
            sa.Column('initiative_roll', sa.Integer(), nullable=True),
        )
        try:
            op.create_index(op.f('ix_combat_participants_id'), 'combat_participants', ['id'], unique=False)
            op.create_index(op.f('ix_combat_participants_actor_id'), 'combat_participants', ['actor_id'], unique=False)
        except Exception:
            pass


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing = inspector.get_table_names()

    if 'combat_participants' in existing:
        op.drop_index(op.f('ix_combat_participants_actor_id'), table_name='combat_participants')
        op.drop_index(op.f('ix_combat_participants_id'), table_name='combat_participants')
        op.drop_table('combat_participants')

    if 'combat_encounters' in existing:
        op.drop_index(op.f('ix_combat_encounters_status'), table_name='combat_encounters')
        op.drop_index(op.f('ix_combat_encounters_id'), table_name='combat_encounters')
        op.drop_table('combat_encounters')
