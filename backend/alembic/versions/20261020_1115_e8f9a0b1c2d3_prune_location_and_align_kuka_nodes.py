"""prune location table and align with KUKA map nodeUuid

Revision ID: e8f9a0b1c2d3
Revises: c3d4e5f6a7b8
Create Date: 2026-10-20 11:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e8f9a0b1c2d3"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop old indexes on columns to be removed
    op.execute(sa.text("""
        DROP INDEX IF EXISTS ix_location_bin_code;
        DROP INDEX IF EXISTS ix_location_bin_code_warehouse;
        DROP INDEX IF EXISTS ix_location_node_label;
        DROP INDEX IF EXISTS ix_location_machine_code;
    """))

    # 2. Add function_type column
    op.execute(sa.text("""
        ALTER TABLE location ADD COLUMN IF NOT EXISTS function_type INTEGER DEFAULT 2;
    """))

    # 3. Expand location_code to VARCHAR(100) to safely store full nodeUuid
    op.execute(sa.text("""
        ALTER TABLE location ALTER COLUMN location_code TYPE VARCHAR(100);
    """))

    # 4. Set location_type default to 'UNASSIGNED'
    op.execute(sa.text("""
        ALTER TABLE location ALTER COLUMN location_type SET DEFAULT 'UNASSIGNED';
    """))

    # 5. Drop deprecated columns from location table
    op.execute(sa.text("""
        ALTER TABLE location DROP COLUMN IF EXISTS bin_code;
        ALTER TABLE location DROP COLUMN IF EXISTS row;
        ALTER TABLE location DROP COLUMN IF EXISTS "column";
        ALTER TABLE location DROP COLUMN IF EXISTS level;
        ALTER TABLE location DROP COLUMN IF EXISTS node_name;
        ALTER TABLE location DROP COLUMN IF EXISTS node_label;
        ALTER TABLE location DROP COLUMN IF EXISTS machine_code;
    """))


def downgrade() -> None:
    op.execute(sa.text("""
        ALTER TABLE location ADD COLUMN IF NOT EXISTS bin_code VARCHAR(50);
        ALTER TABLE location ADD COLUMN IF NOT EXISTS row VARCHAR(10);
        ALTER TABLE location ADD COLUMN IF NOT EXISTS "column" VARCHAR(10);
        ALTER TABLE location ADD COLUMN IF NOT EXISTS level VARCHAR(10);
        ALTER TABLE location ADD COLUMN IF NOT EXISTS node_name VARCHAR(50);
        ALTER TABLE location ADD COLUMN IF NOT EXISTS node_label VARCHAR(50);
        ALTER TABLE location ADD COLUMN IF NOT EXISTS machine_code VARCHAR(50);
        ALTER TABLE location DROP COLUMN IF EXISTS function_type;
        ALTER TABLE location ALTER COLUMN location_code TYPE VARCHAR(50);
        ALTER TABLE location ALTER COLUMN location_type SET DEFAULT 'RAW_MATERIAL';
    """))
