"""add flavor_context to locations

Revision ID: 001_add_flavor_context
Revises: 
Create Date: 2025-11-22 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_add_flavor_context'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('locations', sa.Column('flavor_context', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('locations', 'flavor_context')
