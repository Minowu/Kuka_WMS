"""Item stock model for warehouse cell inventory."""

from sqlalchemy import (
    CheckConstraint,
    UniqueConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
    Boolean,
    case,
    or_,
    func,
    select,
    and_,
)
from sqlalchemy.orm import relationship, column_property
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.core.database import Base
from app.modules.warehouse.outbound_order.outbound_order_model import OutboundOrderAllocation

_NON_COUNTABLE_ALLOCATION_STATUSES = ("completed", "failed")
def countable_allocation_quantity():
    return case(
        (
            and_(
                OutboundOrderAllocation.allocation_type == "outbound",
                OutboundOrderAllocation.status.notin_(_NON_COUNTABLE_ALLOCATION_STATUSES),
            ),
            OutboundOrderAllocation.quantity,
        ),
        else_=0,
    )
def pick_allocated_sum():
    return func.coalesce(func.sum(countable_allocation_quantity()), 0)


class ItemStock(Base):
    """Current item stock rows stored in warehouse locations."""

    __tablename__ = "item_stock"

    id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True, default=uuid.uuid4)
    item_id = Column("item_id", Integer, ForeignKey("item.id"), nullable=False, index=True)
    location_id = Column(
        "location_id",
        Integer,
        ForeignKey("location.id"),
        nullable=True,
        index=True,
    )
    inbound_order_detail_id = Column(Integer, ForeignKey("inbound_order_detail.id"), nullable=True, index=True)
    unit_id = Column(Integer, ForeignKey("unit.id"), nullable=False, index=True)
    quantity = Column(Numeric(12, 3), nullable=False, default=0)
    lot_number_from = Column(String(50), nullable=True, index=True)
    lot_number_to = Column(String(50), nullable=True, index=True)
    expiry_date = Column(String(50), nullable=True, index=True)
    status = Column(
        String(20),
        nullable=False,
        default="available",
        server_default="available",
        index=True,
    )
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    qc_user = Column(String(50), nullable=True, index=True)
    manufacturing_machine = Column(String(50), nullable=True, index=True)
    manufacturing_user = Column(String(50), nullable=True, index=True)
    packing_user = Column(String(50), nullable=True, index=True)
    cavity_number = Column(String(50), nullable=True, index=True)

    stock_level = Column(Integer, nullable=True, index=True)

    # WIP Cart & AMR Dispatching fields
    cart_code = Column(String(50), unique=True, nullable=True, index=True)
    current_stage_level = Column(Integer, nullable=False, default=0, server_default="0")
    is_locked = Column(Boolean, nullable=False, default=False, server_default="false")
    locked_by_task_id = Column(String(100), nullable=True)
    destination_location_id = Column(
        Integer,
        ForeignKey("location.id"),
        nullable=True,
        index=True,
    )

    item = relationship("Item", lazy="joined")
    unit = relationship("Unit", foreign_keys=[unit_id], lazy="joined")
    location = relationship(
        "Location",
        foreign_keys=[location_id],
        back_populates="stocks",
        lazy="joined"
    )
    destination_location = relationship(
        "Location",
        foreign_keys=[destination_location_id],
        lazy="joined"
    )
    inbound_order_detail = relationship("InboundOrderDetail", foreign_keys=[inbound_order_detail_id], lazy="joined")
    available_quantity = column_property(
        quantity
        - select(
            func.coalesce(
                func.sum(countable_allocation_quantity()),
                0,
            )
        )
        .where(OutboundOrderAllocation.item_stock_id == id)
        .correlate_except(OutboundOrderAllocation)
        .scalar_subquery()
    )

    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_item_stock_quantity_non_negative"),
        # CheckConstraint(
        #     "status IN ('available', 'reserved', 'cross_dock_reserved', "
        #     "'in_transit', 'at_outbound_station', 'damaged', 'quarantine', 'expired')",
        #     name="ck_item_stock_status",
        # ),
    )


def countable_stock_level_criterion(stock_level_col=None):
    """Pack/sub-level stock (level > 1) is excluded from item/location inventory views."""
    if stock_level_col is None:
        stock_level_col = ItemStock.stock_level
    return or_(stock_level_col.is_(None), stock_level_col <= 1)


def positive_stock_quantity_criterion(quantity_col=None):
    """Depleted stock rows (quantity = 0) are excluded from inventory read views."""
    if quantity_col is None:
        quantity_col = ItemStock.quantity
    return quantity_col > 0


class ItemStockRelation(Base):
    __tablename__ = "item_stock_relation"

    id = Column(Integer, primary_key=True, index=True)
    parent_stock_id = Column(
        Integer,
        ForeignKey("item_stock.id"),
        nullable=False,
        index=True
    )

    child_stock_id = Column(
        Integer,
        ForeignKey("item_stock.id"),
        nullable=False,
        index=True
    )

    relation_type = Column(
        String(50),
        nullable=False,
        index=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    parent_stock = relationship(
        "ItemStock",
        foreign_keys=[parent_stock_id]
    )

    child_stock = relationship(
        "ItemStock",
        foreign_keys=[child_stock_id]
    )

    __table_args__ = (
        UniqueConstraint(
            "parent_stock_id",
            "child_stock_id",
            "relation_type",
            name="uq_stock_relation"
        ),
        CheckConstraint(
            "parent_stock_id <> child_stock_id",
            name="chk_no_self_reference"
        ),
    )

