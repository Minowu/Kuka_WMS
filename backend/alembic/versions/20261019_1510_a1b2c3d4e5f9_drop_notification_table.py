"""drop notification table

Revision ID: a1b2c3d4e5f9
Revises: f8a9b0c1d2e3
Create Date: 2026-10-19 15:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f9"
down_revision: Union[str, None] = "f8a9b0c1d2e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop physical notification table per user request to streamline database to core 21 tables
    op.execute(sa.text("DROP TABLE IF EXISTS notification CASCADE;"))


def downgrade() -> None:
    op.create_table(
        "notification",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("warehouse.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("action", sa.String(255), nullable=False),
        sa.Column("notification_type", sa.String(50), nullable=False, server_default="alert"),
        sa.Column("status", sa.String(50), nullable=False, server_default="unsolved"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
