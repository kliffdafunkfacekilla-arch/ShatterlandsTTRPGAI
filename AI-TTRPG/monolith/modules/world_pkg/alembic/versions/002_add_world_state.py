"""add world state tracking fields

Revision ID: 002_add_world_state
Revises: 001_add_flavor_context
Create Date: 2025-11-22 14:06:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_add_world_state'
down_revision = '001_add_flavor_context'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add kingdom_resource_level to regions table
    op.add_column('regions', sa.Column('kingdom_resource_level', sa.Integer(), nullable=True))
    
    # Add player_reputation and last_combat_outcome to locations table
    op.add_column('locations', sa.Column('player_reputation', sa.Integer(), nullable=True))
    op.add_column('locations', sa.Column('last_combat_outcome', sa.String(), nullable=True))
    
    # Set default values for existing rows
    op.execute("UPDATE regions SET kingdom_resource_level = 50 WHERE kingdom_resource_level IS NULL")
    op.execute("UPDATE locations SET player_reputation = 0 WHERE player_reputation IS NULL")


def downgrade() -> None:
    # Remove columns in reverse order
    op.drop_column('locations', 'last_combat_outcome')
    op.drop_column('locations', 'player_reputation')
    op.drop_column('regions', 'kingdom_resource_level')
