"""add simulation tables and update factions

Revision ID: 005_add_simulation_tables
Revises: 004_add_campaign_scoping
Create Date: 2025-11-26 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005_add_simulation_tables'
down_revision = '004_add_campaign_scoping'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    # Update factions table
    columns = [c['name'] for c in inspector.get_columns('factions')]
    if 'goals' not in columns:
        op.add_column('factions', sa.Column('goals', sa.String(), nullable=True))
    if 'strength' not in columns:
        op.add_column('factions', sa.Column('strength', sa.Integer(), server_default='50'))
    if 'relationship_matrix' not in columns:
        op.add_column('factions', sa.Column('relationship_matrix', sa.JSON(), server_default='{}'))

    # Create world_resources table
    if 'world_resources' not in inspector.get_table_names():
        op.create_table('world_resources',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('type', sa.String(), nullable=True),
            sa.Column('owner_faction_id', sa.Integer(), nullable=True),
            sa.Column('abundance_level', sa.Integer(), server_default='50', nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['owner_faction_id'], ['factions.id'], )
        )
        op.create_index(op.f('ix_world_resources_id'), 'world_resources', ['id'], unique=False)

    # Create world_state table
    if 'world_state' not in inspector.get_table_names():
        op.create_table('world_state',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('current_tension', sa.Integer(), server_default='0', nullable=True),
            sa.Column('turn_count', sa.Integer(), server_default='0', nullable=True),
            sa.Column('recent_events', sa.JSON(), server_default='[]', nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_world_state_id'), 'world_state', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_world_state_id'), table_name='world_state')
    op.drop_table('world_state')
    
    op.drop_index(op.f('ix_world_resources_id'), table_name='world_resources')
    op.drop_table('world_resources')
    
    op.drop_column('factions', 'relationship_matrix')
    op.drop_column('factions', 'strength')
    op.drop_column('factions', 'goals')
