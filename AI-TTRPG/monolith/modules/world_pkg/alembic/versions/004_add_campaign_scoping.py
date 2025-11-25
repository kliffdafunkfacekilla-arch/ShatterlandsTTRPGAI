"""add campaign_id to world tables

Revision ID: 004_add_campaign_scoping
Revises: 003_add_game_state
Create Date: 2025-11-25 18:18:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004_add_campaign_scoping'
down_revision = '003_add_game_state'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add campaign_id columns to world tables for campaign data isolation
    op.add_column('factions', sa.Column('campaign_id', sa.Integer(), nullable=True))
    op.create_index('ix_factions_campaign_id', 'factions', ['campaign_id'])
    
    op.add_column('regions', sa.Column('campaign_id', sa.Integer(), nullable=True))
    op.create_index('ix_regions_campaign_id', 'regions', ['campaign_id'])
    
    op.add_column('locations', sa.Column('campaign_id', sa.Integer(), nullable=True))
    op.create_index('ix_locations_campaign_id', 'locations', ['campaign_id'])
    
    # Set default campaign_id = 1 for existing data (backward compatibility)
    op.execute("UPDATE factions SET campaign_id = 1 WHERE campaign_id IS NULL")
    op.execute("UPDATE regions SET campaign_id = 1 WHERE campaign_id IS NULL")
    op.execute("UPDATE locations SET campaign_id = 1 WHERE campaign_id IS NULL")


def downgrade() -> None:
    # Remove campaign scoping
    op.drop_index('ix_locations_campaign_id', 'locations')
    op.drop_column('locations', 'campaign_id')
    
    op.drop_index('ix_regions_campaign_id', 'regions')
    op.drop_column('regions', 'campaign_id')
    
    op.drop_index('ix_factions_campaign_id', 'factions')
    op.drop_column('factions', 'campaign_id')
