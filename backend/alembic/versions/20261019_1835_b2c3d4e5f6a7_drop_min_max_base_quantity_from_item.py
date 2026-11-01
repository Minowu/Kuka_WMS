"""drop min_quantity, max_quantity, and base_quantity from item table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f9
Create Date: 2026-10-19 18:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop min_quantity, max_quantity, base_quantity from item table as they are not needed for CNC machining
    op.execute(sa.text("""
        ALTER TABLE item DROP COLUMN IF EXISTS min_quantity;
        ALTER TABLE item DROP COLUMN IF EXISTS max_quantity;
        ALTER TABLE item DROP COLUMN IF EXISTS base_quantity;
    """))


def downgrade() -> None:
    op.add_column("item", sa.Column("base_quantity", sa.BigInteger(), nullable=True, server_default="1"))
    op.add_column("item", sa.Column("max_quantity", sa.Integer(), nullable=True, server_default="999999"))
    op.add_column("item", sa.Column("min_quantity", sa.Integer(), nullable=True, server_default="0"))
