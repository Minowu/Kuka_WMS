"""add_partial_unique_indexes

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
Create Date: 2026-10-19 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f8a9b0c1d2e3"
down_revision: Union[str, None] = "e7f8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enforce at the PostgreSQL physical level: Each item_id can have at most ONE active ProductionRoute
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_production_route_active_per_item
            ON production_route (item_id)
            WHERE is_active IS TRUE;
            """
        )
    )

    # 2. Enforce at the PostgreSQL physical level: Each physical location can have at most ONE active Cart sitting on it
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_item_stock_active_location
            ON item_stock (location_id)
            WHERE is_active IS TRUE AND location_id IS NOT NULL;
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS uq_production_route_active_per_item;"))
    op.execute(sa.text("DROP INDEX IF EXISTS uq_item_stock_active_location;"))
