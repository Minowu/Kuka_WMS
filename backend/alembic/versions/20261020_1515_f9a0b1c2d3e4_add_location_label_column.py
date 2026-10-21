"""add location_label column to location table

Revision ID: f9a0b1c2d3e4
Revises: e8f9a0b1c2d3
Create Date: 2026-10-20 15:15:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f9a0b1c2d3e4'
down_revision = 'e8f9a0b1c2d3'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('location', sa.Column('location_label', sa.String(length=50), nullable=True))
    op.create_index(op.f('ix_location_location_label'), 'location', ['location_label'], unique=False)
    # Sao chep location_name sang location_label cho cac ban ghi hien co
    op.execute("UPDATE location SET location_label = location_name WHERE location_label IS NULL AND location_name IS NOT NULL;")


def downgrade():
    op.drop_index(op.f('ix_location_location_label'), table_name='location')
    op.drop_column('location', 'location_label')
