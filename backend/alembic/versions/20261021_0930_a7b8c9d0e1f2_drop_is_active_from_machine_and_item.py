"""drop is_active from machine and item

Revision ID: a7b8c9d0e1f2
Revises: f9a0b1c2d3e4
Create Date: 2026-10-21 09:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a7b8c9d0e1f2'
down_revision = 'f9a0b1c2d3e4'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('machine', 'is_active')
    op.drop_column('item', 'is_active')


def downgrade():
    op.add_column('item', sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('machine', sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False))
