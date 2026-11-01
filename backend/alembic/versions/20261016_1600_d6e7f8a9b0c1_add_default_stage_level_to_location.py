"""add_default_stage_level_to_location

Revision ID: d6e7f8a9b0c1
Revises: c5e6f7a8b9d0
Create Date: 2026-10-16 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "d6e7f8a9b0c1"
down_revision: Union[str, None] = "c5e6f7a8b9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    loc_cols = {col["name"] for col in insp.get_columns("location")}
    if "default_stage_level" not in loc_cols:
        op.add_column(
            "location",
            sa.Column("default_stage_level", sa.Integer(), nullable=True),
        )
        op.create_index(
            op.f("ix_location_default_stage_level"),
            "location",
            ["default_stage_level"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    loc_cols = {col["name"] for col in insp.get_columns("location")}
    if "default_stage_level" in loc_cols:
        op.drop_index(op.f("ix_location_default_stage_level"), table_name="location")
        op.drop_column("location", "default_stage_level")
