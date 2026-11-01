from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Numeric, func, JSON, select, table, column, and_, exists, case
)
from sqlalchemy.orm import relationship, column_property
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base

_inbound_order_detail_tbl = table(
    "inbound_order_detail",
    column("inbound_order_id", Integer),
    column("status", String),
)

def _inbound_order_detail_exists(order_id_col, *criteria):
    return exists(
        select(1)
        .where(
            _inbound_order_detail_tbl.c.inbound_order_id == order_id_col,
            *criteria,
        )
        .correlate_except(_inbound_order_detail_tbl)
    )

class InboundOrder(Base):
    """Inbound order header."""
    
    __tablename__ = "inbound_order"
    
    id = Column(Integer, primary_key=True, index=True)
    order_code = Column(String(50), unique=True, nullable=False, index=True)
    note = Column(Text)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouse.id"), nullable=False, index=True)
    details = Column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
        server_default="{}",
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    created_by = relationship("User", foreign_keys=[created_by_id], lazy="joined")
    warehouse = relationship("Warehouse", foreign_keys=[warehouse_id], lazy="joined")

    status = column_property(
        case(
            (
                and_(
                    _inbound_order_detail_exists(id),
                    ~_inbound_order_detail_exists(id, _inbound_order_detail_tbl.c.status != "completed"),
                ),
                "completed",
            ),
            (
                _inbound_order_detail_exists(
                    id,
                    _inbound_order_detail_tbl.c.status.notin_(("initialize",)),
                ),
                "in_progress",
            ),
            else_="initialize",
        )
    )

class InboundOrderDetail(Base):
    """Inbound order detail line items."""

    __tablename__ = "inbound_order_detail"

    id = Column(Integer, primary_key=True, index=True)
    inbound_order_id = Column(
        Integer,
        ForeignKey("inbound_order.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_location_id = Column(Integer, ForeignKey("location.id"), nullable=True, index=True)
    to_location_id = Column(Integer, ForeignKey("location.id"), nullable=True, index=True)
    details = Column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
        server_default="{}",
    )
    status = Column(String(20), default="initialize", nullable=False, index=True)
    detail_type = Column(String(50), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    inbound_order = relationship("InboundOrder", foreign_keys=[inbound_order_id], lazy="joined")
    from_location = relationship("Location", foreign_keys=[from_location_id], lazy="joined")
    to_location = relationship("Location", foreign_keys=[to_location_id], lazy="joined")
    allocations = relationship(
        "InboundOrderAllocation",
        back_populates="inbound_order_detail",
        lazy="selectin",
    )

class InboundOrderAllocation(Base):
    """Inbound order allocation."""

    __tablename__ = "inbound_order_allocation"
    
    id = Column(Integer, primary_key=True, index=True)
    inbound_order_detail_id = Column(Integer, ForeignKey("inbound_order_detail.id"), nullable=False, index=True)
    item_stock_id = Column(Integer, ForeignKey("item_stock.id"), nullable=False, index=True)
    unit_id = Column(Integer, ForeignKey("unit.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    inbound_order_detail = relationship(
        "InboundOrderDetail",
        foreign_keys=[inbound_order_detail_id],
        back_populates="allocations",
        lazy="joined",
    )
    item_stock = relationship("ItemStock", foreign_keys=[item_stock_id], lazy="joined")
    unit = relationship("Unit", foreign_keys=[unit_id], lazy="joined")
    status = column_property(
        select(InboundOrderDetail.status)
        .where(InboundOrderDetail.id == inbound_order_detail_id)
        .correlate_except(InboundOrderDetail)
        .scalar_subquery()
    )