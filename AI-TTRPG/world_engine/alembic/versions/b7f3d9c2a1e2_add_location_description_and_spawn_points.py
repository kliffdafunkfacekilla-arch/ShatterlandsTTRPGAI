"""add location description and spawn_points

Revision ID: b7f3d9c2a1e2
Revises: a4d6d63e365c
Create Date: 2025-11-12 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = 'b7f3d9c2a1e2'
down_revision = 'a4d6d63e365c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add a nullable description and spawn_points columns to locations
    bind = op.get_bind()
    try:
        res = bind.execute(text("PRAGMA table_info('locations')")).fetchall()
        existing = {row[1] for row in res}
    except Exception:
        existing = set()

    if 'description' not in existing:
        op.add_column('locations', sa.Column('description', sa.Text(), nullable=True))

    if 'spawn_points' not in existing:
        # JSON type is supported in SQLite via SQLAlchemy as JSON
        op.add_column('locations', sa.Column('spawn_points', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove the columns on downgrade if they exist
    bind = op.get_bind()
    try:
        res = bind.execute(text("PRAGMA table_info('locations')")).fetchall()
        existing = {row[1] for row in res}
    except Exception:
        existing = set()

    if 'spawn_points' in existing:
        op.drop_column('locations', 'spawn_points')
    if 'description' in existing:
        op.drop_column('locations', 'description')
