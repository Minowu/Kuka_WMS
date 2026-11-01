"""add_production_core_models

Revision ID: c5e6f7a8b9d0
Revises: b3775d08063f
Create Date: 2026-10-16 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "c5e6f7a8b9d0"
down_revision: Union[str, None] = "b3775d08063f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    # 1. Update location table
    loc_cols = {col["name"] for col in insp.get_columns("location")}
    if "location_type" not in loc_cols:
        op.add_column(
            "location",
            sa.Column("location_type", sa.String(length=30), nullable=False, server_default="CNC_SLOT"),
        )
    if "machine_code" not in loc_cols:
        op.add_column(
            "location",
            sa.Column("machine_code", sa.String(length=50), nullable=True),
        )
        op.create_index(op.f("ix_location_machine_code"), "location", ["machine_code"], unique=False)
    if "position_index" not in loc_cols:
        op.add_column(
            "location",
            sa.Column("position_index", sa.Integer(), nullable=True),
        )

    # 2. Update item table
    item_cols = {col["name"] for col in insp.get_columns("item")}
    if "standard_quantity_per_cart" not in item_cols:
        op.add_column(
            "item",
            sa.Column("standard_quantity_per_cart", sa.Integer(), nullable=False, server_default="120"),
        )

    # 3. Update item_stock table
    stock_cols = {col["name"] for col in insp.get_columns("item_stock")}
    if "cart_code" not in stock_cols:
        op.add_column(
            "item_stock",
            sa.Column("cart_code", sa.String(length=50), nullable=True),
        )
        op.create_index(op.f("ix_item_stock_cart_code"), "item_stock", ["cart_code"], unique=True)
    if "current_stage_level" not in stock_cols:
        op.add_column(
            "item_stock",
            sa.Column("current_stage_level", sa.Integer(), nullable=False, server_default="0"),
        )
    if "is_locked" not in stock_cols:
        op.add_column(
            "item_stock",
            sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )
    if "locked_by_task_id" not in stock_cols:
        op.add_column(
            "item_stock",
            sa.Column("locked_by_task_id", sa.String(length=100), nullable=True),
        )
    if "destination_location_id" not in stock_cols:
        op.add_column(
            "item_stock",
            sa.Column("destination_location_id", sa.Integer(), nullable=True),
        )
        op.create_foreign_key(
            "fk_item_stock_destination_location",
            "item_stock",
            "location",
            ["destination_location_id"],
            ["id"],
        )
        op.create_index(
            op.f("ix_item_stock_destination_location_id"),
            "item_stock",
            ["destination_location_id"],
            unique=False,
        )

    # 4. Create user_locations table
    tables = set(insp.get_table_names())
    if "user_locations" not in tables:
        op.create_table(
            "user_locations",
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("location_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["location_id"], ["location.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("user_id", "location_id"),
        )
        op.create_index(op.f("ix_user_locations_user_id"), "user_locations", ["user_id"], unique=False)
        op.create_index(op.f("ix_user_locations_location_id"), "user_locations", ["location_id"], unique=False)

    # 5. Create production_route table
    if "production_route" not in tables:
        op.create_table(
            "production_route",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("route_code", sa.String(length=50), nullable=False),
            sa.Column("route_name", sa.String(length=100), nullable=False),
            sa.Column("item_id", sa.Integer(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["item_id"], ["item.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_production_route_id"), "production_route", ["id"], unique=False)
        op.create_index(op.f("ix_production_route_route_code"), "production_route", ["route_code"], unique=True)
        op.create_index(op.f("ix_production_route_item_id"), "production_route", ["item_id"], unique=False)

    # 6. Create route_step table
    if "route_step" not in tables:
        op.create_table(
            "route_step",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("route_id", sa.Integer(), nullable=False),
            sa.Column("step_number", sa.Integer(), nullable=False),
            sa.Column("stage_level", sa.Integer(), nullable=False),
            sa.Column("step_name", sa.String(length=100), nullable=False),
            sa.Column("allowed_machines", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
            sa.Column("is_final_cnc_step", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["route_id"], ["production_route.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("route_id", "step_number", name="uq_route_step_number"),
        )
        op.create_index(op.f("ix_route_step_id"), "route_step", ["id"], unique=False)
        op.create_index(op.f("ix_route_step_route_id"), "route_step", ["route_id"], unique=False)
        op.create_index("idx_route_step_lookup", "route_step", ["route_id", "stage_level"], unique=False)

    # 7. Create transport_request table
    if "transport_request" not in tables:
        op.create_table(
            "transport_request",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("request_code", sa.String(length=50), nullable=False),
            sa.Column("request_type", sa.String(length=50), nullable=False, server_default="CALL_MATERIAL"),
            sa.Column("item_id", sa.Integer(), nullable=True),
            sa.Column("source_location_id", sa.Integer(), nullable=True),
            sa.Column("destination_location_id", sa.Integer(), nullable=False),
            sa.Column("cart_id", sa.Integer(), nullable=True),
            sa.Column("required_stage_level", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="10"),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["item_id"], ["item.id"]),
            sa.ForeignKeyConstraint(["source_location_id"], ["location.id"]),
            sa.ForeignKeyConstraint(["destination_location_id"], ["location.id"]),
            sa.ForeignKeyConstraint(["cart_id"], ["item_stock.id"]),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_transport_request_id"), "transport_request", ["id"], unique=False)
        op.create_index(op.f("ix_transport_request_request_code"), "transport_request", ["request_code"], unique=True)
        op.create_index(op.f("ix_transport_request_status"), "transport_request", ["status"], unique=False)
        op.create_index(op.f("ix_transport_request_destination_location_id"), "transport_request", ["destination_location_id"], unique=False)

    # 8. Create transport_queue table
    if "transport_queue" not in tables:
        op.create_table(
            "transport_queue",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("request_id", sa.Integer(), nullable=False),
            sa.Column("queue_type", sa.String(length=30), nullable=False),
            sa.Column("target_stage_level", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="PENDING"),
            sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="10"),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["request_id"], ["transport_request.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_transport_queue_id"), "transport_queue", ["id"], unique=False)
        op.create_index(op.f("ix_transport_queue_request_id"), "transport_queue", ["request_id"], unique=False)
        op.create_index(op.f("ix_transport_queue_status"), "transport_queue", ["status"], unique=False)
        op.create_index("idx_transport_queue_active", "transport_queue", ["queue_type", "status", "priority"], unique=False)

    # 9. Create fleet_task table
    if "fleet_task" not in tables:
        op.create_table(
            "fleet_task",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("task_code", sa.String(length=50), nullable=False),
            sa.Column("request_id", sa.Integer(), nullable=False),
            sa.Column("amr_code", sa.String(length=50), nullable=True),
            sa.Column("pickup_location_id", sa.Integer(), nullable=False),
            sa.Column("dropoff_location_id", sa.Integer(), nullable=False),
            sa.Column("cart_id", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="created"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["request_id"], ["transport_request.id"]),
            sa.ForeignKeyConstraint(["pickup_location_id"], ["location.id"]),
            sa.ForeignKeyConstraint(["dropoff_location_id"], ["location.id"]),
            sa.ForeignKeyConstraint(["cart_id"], ["item_stock.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_fleet_task_id"), "fleet_task", ["id"], unique=False)
        op.create_index(op.f("ix_fleet_task_task_code"), "fleet_task", ["task_code"], unique=True)
        op.create_index(op.f("ix_fleet_task_status"), "fleet_task", ["status"], unique=False)

    # 10. Create production_record table
    if "production_record" not in tables:
        op.create_table(
            "production_record",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("cart_code", sa.String(length=50), nullable=False),
            sa.Column("cart_id", sa.Integer(), nullable=True),
            sa.Column("item_id", sa.Integer(), nullable=False),
            sa.Column("machine_code", sa.String(length=50), nullable=True),
            sa.Column("location_id", sa.Integer(), nullable=False),
            sa.Column("stage_level", sa.Integer(), nullable=False),
            sa.Column("operator_id", sa.Integer(), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["cart_id"], ["item_stock.id"]),
            sa.ForeignKeyConstraint(["item_id"], ["item.id"]),
            sa.ForeignKeyConstraint(["location_id"], ["location.id"]),
            sa.ForeignKeyConstraint(["operator_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_production_record_id"), "production_record", ["id"], unique=False)
        op.create_index(op.f("ix_production_record_cart_code"), "production_record", ["cart_code"], unique=False)
        op.create_index(op.f("ix_production_record_location_id"), "production_record", ["location_id"], unique=False)


def downgrade() -> None:
    op.drop_table("production_record")
    op.drop_table("fleet_task")
    op.drop_table("transport_queue")
    op.drop_table("transport_request")
    op.drop_table("route_step")
    op.drop_table("production_route")
    op.drop_table("user_locations")

    op.drop_constraint("fk_item_stock_destination_location", "item_stock", type_="foreignkey")
    op.drop_index(op.f("ix_item_stock_destination_location_id"), table_name="item_stock")
    op.drop_index(op.f("ix_item_stock_cart_code"), table_name="item_stock")
    op.drop_column("item_stock", "destination_location_id")
    op.drop_column("item_stock", "locked_by_task_id")
    op.drop_column("item_stock", "is_locked")
    op.drop_column("item_stock", "current_stage_level")
    op.drop_column("item_stock", "cart_code")

    op.drop_column("item", "standard_quantity_per_cart")

    op.drop_index(op.f("ix_location_machine_code"), table_name="location")
    op.drop_column("location", "position_index")
    op.drop_column("location", "machine_code")
    op.drop_column("location", "location_type")
