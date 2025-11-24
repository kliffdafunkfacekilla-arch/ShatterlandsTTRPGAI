"""add reactive state to game_state table

Revision ID: 003_add_game_state
Revises: 002_add_world_state
Create Date: 2025-11-23 10:55:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB # Use sa.JSON if not using Postgres

# revision identifiers, used by Alembic.
revision = '003_add_game_state'
down_revision = '002_add_world_state'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Create the new table
    op.create_table(
        'game_state',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('player_reputation', sa.Integer(), nullable=False, default=0),
        sa.Column('kingdom_resource_level', sa.Integer(), nullable=False, default=100),
        sa.Column('last_map_flavor_context', sa.JSON(), nullable=True),
        sa.Column('last_event_text', sa.String(), nullable=True),
    )
    
    # 2. Insert the single required row with default values
    # This ensures the table always has the row with ID 1 ready to be updated.
    op.execute(
        sa.insert(
            sa.table(
                'game_state',
                sa.column('id'),
                sa.column('player_reputation'),
                sa.column('kingdom_resource_level')
            )
        ).values(
            id=1,
            player_reputation=0,
            kingdom_resource_level=100
        )
    )

def downgrade() -> None:
    # Drop the table on downgrade
    op.drop_table('game_state')
