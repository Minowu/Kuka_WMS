"""normalize_3nf_machine_drop_zone_and_add_task_status

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-10-19 00:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "e7f8a9b0c1d2"
down_revision: Union[str, None] = "d6e7f8a9b0c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    tables = set(insp.get_table_names())

    # 1. Create machine table (3NF)
    if "machine" not in tables:
        op.create_table(
            "machine",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("machine_code", sa.String(length=50), nullable=False),
            sa.Column("machine_name", sa.String(length=100), nullable=True),
            sa.Column("default_stage_level", sa.Integer(), nullable=True),
            sa.Column("warehouse_id", sa.Integer(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["warehouse_id"], ["warehouse.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_machine_id"), "machine", ["id"], unique=False)
        op.create_index(op.f("ix_machine_machine_code"), "machine", ["machine_code"], unique=True)
        op.create_index(op.f("ix_machine_default_stage_level"), "machine", ["default_stage_level"], unique=False)
        op.create_index(op.f("ix_machine_warehouse_id"), "machine", ["warehouse_id"], unique=False)

    # 2. Add machine_id to location and populate from location.machine_code
    loc_cols = {col["name"] for col in insp.get_columns("location")}
    if "machine_id" not in loc_cols:
        op.add_column("location", sa.Column("machine_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_location_machine_id",
            "location",
            "machine",
            ["machine_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index(op.f("ix_location_machine_id"), "location", ["machine_id"], unique=False)

    # Backfill machine table from existing location.machine_code
    bind.execute(
        sa.text(
            """
            INSERT INTO machine (machine_code, machine_name, default_stage_level, warehouse_id, is_active)
            SELECT DISTINCT
                machine_code,
                'Máy ' || machine_code,
                MAX(default_stage_level),
                MIN(warehouse_id),
                true
            FROM location
            WHERE machine_code IS NOT NULL AND TRIM(machine_code) <> ''
            GROUP BY machine_code
            ON CONFLICT (machine_code) DO NOTHING
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE location l
            SET machine_id = m.id
            FROM machine m
            WHERE l.machine_code = m.machine_code AND l.machine_id IS NULL
            """
        )
    )

    # 3. Create route_step_machine join table (3NF)
    if "route_step_machine" not in tables:
        op.create_table(
            "route_step_machine",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("route_step_id", sa.Integer(), nullable=False),
            sa.Column("machine_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["route_step_id"], ["route_step.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["machine_id"], ["machine.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("route_step_id", "machine_id", name="uq_route_step_machine"),
        )
        op.create_index(op.f("ix_route_step_machine_id"), "route_step_machine", ["id"], unique=False)
        op.create_index(op.f("ix_route_step_machine_route_step_id"), "route_step_machine", ["route_step_id"], unique=False)
        op.create_index(op.f("ix_route_step_machine_machine_id"), "route_step_machine", ["machine_id"], unique=False)

    # 4. Migrate existing route_step.allowed_machines JSON array into route_step_machine, then drop redundant columns
    step_cols = {col["name"] for col in insp.get_columns("route_step")}
    if "allowed_machines" in step_cols:
        bind.execute(
            sa.text(
                """
                INSERT INTO machine (machine_code, machine_name, is_active)
                SELECT DISTINCT
                    jsonb_array_elements_text(allowed_machines::jsonb) AS code,
                    'Máy ' || jsonb_array_elements_text(allowed_machines::jsonb),
                    true
                FROM route_step
                WHERE allowed_machines IS NOT NULL
                ON CONFLICT (machine_code) DO NOTHING
                """
            )
        )
        bind.execute(
            sa.text(
                """
                INSERT INTO route_step_machine (route_step_id, machine_id)
                SELECT DISTINCT
                    rs.id,
                    m.id
                FROM route_step rs
                CROSS JOIN LATERAL jsonb_array_elements_text(rs.allowed_machines::jsonb) AS code
                JOIN machine m ON m.machine_code = code
                WHERE rs.allowed_machines IS NOT NULL
                ON CONFLICT (route_step_id, machine_id) DO NOTHING
                """
            )
        )

    for col_to_drop in (
        "operation_code",
        "machine_type",
        "program_number",
        "cycle_time_minutes",
        "allowed_machines",
    ):
        if col_to_drop in step_cols:
            op.drop_column("route_step", col_to_drop)

    # 5. Update fleet_task and ensure task_status table exists for KUKA Fleet callbacks
    fleet_cols = {col["name"] for col in insp.get_columns("fleet_task")}
    if "process_code" not in fleet_cols:
        op.add_column("fleet_task", sa.Column("process_code", sa.String(length=50), nullable=True))
    if "system_code" not in fleet_cols:
        op.add_column(
            "fleet_task",
            sa.Column("system_code", sa.String(length=50), nullable=True, server_default="MES"),
        )
    if "task_order_detail" not in fleet_cols:
        op.add_column("fleet_task", sa.Column("task_order_detail", sa.Text(), nullable=True))

    if "task_status" not in tables:
        op.create_table(
            "task_status",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("sub_task_status", sa.String(length=50), nullable=True),
            sa.Column("order_id", sa.String(length=50), nullable=True),
            sa.Column("device_code", sa.String(length=50), nullable=True),
            sa.Column("device_num", sa.String(length=50), nullable=True),
            sa.Column("qr_code", sa.String(length=255), nullable=True),
            sa.Column("shelf_number", sa.String(length=50), nullable=True),
            sa.Column("status", sa.String(length=50), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_task_status_id"), "task_status", ["id"], unique=False)
        op.create_index(op.f("ix_task_status_order_id"), "task_status", ["order_id"], unique=False)

    # 6. Drop zone_id from location and warehouse_map, then drop zone table
    if "zone_id" in loc_cols:
        for fk in insp.get_foreign_keys("location"):
            if "zone_id" in fk.get("constrained_columns", []):
                op.drop_constraint(fk["name"], "location", type_="foreignkey")
        for idx in insp.get_indexes("location"):
            if idx.get("column_names") == ["zone_id"]:
                op.drop_index(idx["name"], table_name="location")
        op.drop_column("location", "zone_id")

    if "warehouse_map" in tables:
        wm_cols = {col["name"] for col in insp.get_columns("warehouse_map")}
        if "zone_id" in wm_cols:
            for fk in insp.get_foreign_keys("warehouse_map"):
                if "zone_id" in fk.get("constrained_columns", []):
                    op.drop_constraint(fk["name"], "warehouse_map", type_="foreignkey")
            for idx in insp.get_indexes("warehouse_map"):
                if idx.get("column_names") == ["zone_id"]:
                    op.drop_index(idx["name"], table_name="warehouse_map")
            op.drop_column("warehouse_map", "zone_id")

    if "zone" in tables:
        op.execute(sa.text("DROP TABLE IF EXISTS zone CASCADE"))


def downgrade() -> None:
    pass
