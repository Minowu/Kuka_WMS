"""drop default_stage_level from machine and location, add node_label to location, cleanup mock locations

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-10-19 19:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop indexes on default_stage_level if they exist
    op.execute(sa.text("""
        DROP INDEX IF EXISTS ix_machine_default_stage_level;
        DROP INDEX IF EXISTS ix_location_default_stage_level;
    """))

    # 2. Drop default_stage_level column from machine and location
    op.execute(sa.text("""
        ALTER TABLE machine DROP COLUMN IF EXISTS default_stage_level;
        ALTER TABLE location DROP COLUMN IF EXISTS default_stage_level;
    """))

    # 3. Add node_label column to location
    op.execute(sa.text("""
        ALTER TABLE location ADD COLUMN IF NOT EXISTS node_label VARCHAR(50);
        CREATE INDEX IF NOT EXISTS ix_location_node_label ON location (node_label);
    """))

    # 4. Clean up mock / duplicate unassigned raw node locations created during initial map import
    # that are not linked to machines and have no active stock
    op.execute(sa.text("""
        DELETE FROM location 
        WHERE location_code IN ('189', '188', '2', '1', '51', '50', '4', '17', '18', '20', '23', '24', '25', '26', '40', '41', '42', '127', '128', '129', '130', '216', '249')
          AND machine_id IS NULL
          AND id NOT IN (SELECT DISTINCT location_id FROM item_stock WHERE location_id IS NOT NULL);
    """))


def downgrade() -> None:
    op.execute(sa.text("""
        DROP INDEX IF EXISTS ix_location_node_label;
        ALTER TABLE location DROP COLUMN IF EXISTS node_label;
        ALTER TABLE machine ADD COLUMN IF EXISTS default_stage_level INTEGER;
        ALTER TABLE location ADD COLUMN IF EXISTS default_stage_level INTEGER;
        CREATE INDEX IF NOT EXISTS ix_machine_default_stage_level ON machine (default_stage_level);
        CREATE INDEX IF NOT EXISTS ix_location_default_stage_level ON location (default_stage_level);
    """))
