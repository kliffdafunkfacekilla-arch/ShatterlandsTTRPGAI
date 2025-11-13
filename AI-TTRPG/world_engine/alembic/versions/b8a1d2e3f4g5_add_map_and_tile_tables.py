"""add map and tile tables for layered/nested world maps

Revision ID: b8a1d2e3f4g5
Revises: b7f3d9c2a1e2
Create Date: 2025-11-12 00:10:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b8a1d2e3f4g5'
down_revision = 'b7f3d9c2a1e2'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'maps',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(), index=True),
        sa.Column('parent_map_id', sa.Integer(), sa.ForeignKey('maps.id'), nullable=True),
        sa.Column('grid_width', sa.Integer(), default=100),
        sa.Column('grid_height', sa.Integer(), default=100),
        sa.Column('layers', sa.Integer(), default=1),
        sa.Column('description', sa.Text(), nullable=True),
    )
    op.create_table(
        'tiles',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('map_id', sa.Integer(), sa.ForeignKey('maps.id')),
        sa.Column('x', sa.Integer()),
        sa.Column('y', sa.Integer()),
        sa.Column('z', sa.Integer(), default=0),
        sa.Column('terrain', sa.String(), nullable=True),
        sa.Column('features', sa.JSON(), default={}),
        sa.Column('nested_map_id', sa.Integer(), sa.ForeignKey('maps.id'), nullable=True),
    )

def downgrade() -> None:
    op.drop_table('tiles')
    op.drop_table('maps')