"""add missing columns

Revision ID: 006_add_missing_columns
Revises: 005_add_simulation_tables
Create Date: 2025-11-26 18:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006_add_missing_columns'
down_revision = '005_add_simulation_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    # Regions
    cols = [c['name'] for c in inspector.get_columns('regions')]
    if 'kingdom_resource_level' not in cols:
        op.add_column('regions', sa.Column('kingdom_resource_level', sa.Integer(), server_default='50'))

    # Locations
    cols = [c['name'] for c in inspector.get_columns('locations')]
    if 'player_reputation' not in cols:
        op.add_column('locations', sa.Column('player_reputation', sa.Integer(), server_default='0'))
    if 'last_combat_outcome' not in cols:
        op.add_column('locations', sa.Column('last_combat_outcome', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('locations', 'last_combat_outcome')
    op.drop_column('locations', 'player_reputation')
    op.drop_column('regions', 'kingdom_resource_level')
