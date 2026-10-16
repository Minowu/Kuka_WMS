from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Numeric, func, JSON, select, table, column, and_, exists, case, or_
)
from sqlalchemy.orm import relationship, column_property
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base

_outbound_order_detail_tbl = table(
    "outbound_order_detail",
    column("id", Integer),
    column("outbound_order_id", Integer),
    column("quantity", Integer),
)

_outbound_order_allocation_tbl = table(
    "outbound_order_allocation",
    column("outbound_order_detail_id", Integer),
    column("status", String),
    column("quantity", Integer),           
    column("allocation_type", String),
)

def _outbound_order_has_detail_status(order_id_col, status_value: str):
    return exists(
        select(1)
        .select_from(_outbound_order_detail_tbl)
        .where(
            _outbound_order_detail_tbl.c.outbound_order_id == order_id_col,
            _outbound_detail_status_expr(
                _outbound_order_detail_tbl.c.id,
                _outbound_order_detail_tbl.c.quantity,
            ) == status_value,
        )
        .correlate_except(_outbound_order_detail_tbl)
    )

def _outbound_order_all_details_status(order_id_col, status_value: str):
    return and_(
        exists(
            select(1)
            .select_from(_outbound_order_detail_tbl)
            .where(_outbound_order_detail_tbl.c.outbound_order_id == order_id_col)
            .correlate_except(_outbound_order_detail_tbl)
        ),
        ~exists(
            select(1)
            .select_from(_outbound_order_detail_tbl)
            .where(
                _outbound_order_detail_tbl.c.outbound_order_id == order_id_col,
                _outbound_detail_status_expr(
                    _outbound_order_detail_tbl.c.id,
                    _outbound_order_detail_tbl.c.quantity,
                ) != status_value,
            )
            .correlate_except(_outbound_order_detail_tbl)
        ),
    )

def _outbound_detail_status_expr(detail_id_col, quantity_col):
    return case(
        (
            or_(
                and_(
                    _outbound_order_allocation_exists(detail_id_col),
                    quantity_col != _outbound_allocated_quantity(detail_id_col),
                ),
                and_(
                    _outbound_order_allocation_exists(
                        detail_id_col,
                        _outbound_order_allocation_tbl.c.status != "initialize",
                    ),
                    _outbound_order_allocation_exists(
                        detail_id_col,
                        _outbound_order_allocation_tbl.c.status != "completed",
                    ),
                ),
            ),
            "in_progress",
        ),
        (
            and_(
                _outbound_order_allocation_exists(detail_id_col),
                ~_outbound_order_allocation_exists(
                    detail_id_col,
                    _outbound_order_allocation_tbl.c.status != "completed",
                ),
            ),
            "completed",
        ),
        (
            _outbound_order_allocation_exists(
                detail_id_col,
                _outbound_order_allocation_tbl.c.status == "initialize",
            ),
            "reserved",
        ),
        else_="initialize",
    )

def _outbound_order_has_any_detail(order_id_col):
    return exists(
        select(1)
        .select_from(_outbound_order_detail_tbl)
        .where(_outbound_order_detail_tbl.c.outbound_order_id == order_id_col)
        .correlate_except(_outbound_order_detail_tbl)
    )

def _outbound_order_has_detail_status(order_id_col, status_value: str):
    return exists(
        select(1)
        .select_from(_outbound_order_detail_tbl)
        .where(
            _outbound_order_detail_tbl.c.outbound_order_id == order_id_col,
            _outbound_detail_status_expr(
                _outbound_order_detail_tbl.c.id,
                _outbound_order_detail_tbl.c.quantity,
            ) == status_value,
        )
        .correlate_except(_outbound_order_detail_tbl)
    )

def _outbound_order_all_details_status(order_id_col, status_value: str):
    return and_(
        exists(
            select(1)
            .select_from(_outbound_order_detail_tbl)
            .where(_outbound_order_detail_tbl.c.outbound_order_id == order_id_col)
            .correlate_except(_outbound_order_detail_tbl)
        ),
        ~exists(
            select(1)
            .select_from(_outbound_order_detail_tbl)
            .where(
                _outbound_order_detail_tbl.c.outbound_order_id == order_id_col,
                _outbound_detail_status_expr(
                    _outbound_order_detail_tbl.c.id,
                    _outbound_order_detail_tbl.c.quantity,
                ) != status_value,
            )
            .correlate_except(_outbound_order_detail_tbl)
        ),
    )

def _outbound_allocated_quantity(detail_id_col):
    return (
        select(
            func.coalesce(
                func.sum(
                    case(
                        (
                            _outbound_order_allocation_tbl.c.allocation_type == "return",
                            0,
                        ),
                        else_=_outbound_order_allocation_tbl.c.quantity,
                    )
                ),
                0,
            )
        )
        .where(
            _outbound_order_allocation_tbl.c.outbound_order_detail_id == detail_id_col,
        )
        .correlate_except(_outbound_order_allocation_tbl)
        .scalar_subquery()
    )

def _outbound_order_allocation_exists(detail_id_col, *criteria):
    return exists(
        select(1)
        .where(
            _outbound_order_allocation_tbl.c.outbound_order_detail_id == detail_id_col,
            *criteria,
        )
        .correlate_except(_outbound_order_allocation_tbl)
    )


class OutboundOrder(Base):
    """Outbound order header."""
    
    __tablename__ = "outbound_order"
    
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
                or_(
                    _outbound_order_has_detail_status(id, "in_progress"),
                    and_(
                        _outbound_order_has_any_detail(id),
                        ~_outbound_order_all_details_status(id, "completed"),
                        ~_outbound_order_all_details_status(id, "reserved"),
                        ~_outbound_order_all_details_status(id, "initialize"),
                    ),
                ),
                "in_progress",
            ),
            (
                _outbound_order_all_details_status(id, "completed"),
                "completed",
            ),
            (
                _outbound_order_all_details_status(id, "reserved"),
                "reserved",
            ),
            else_="initialize",
        )
    )

class OutboundOrderDetail(Base):
    """Outbound order detail line items."""

    __tablename__ = "outbound_order_detail"

    id = Column(Integer, primary_key=True, index=True)
    outbound_order_id = Column(
        Integer,
        ForeignKey("outbound_order.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_id = Column(Integer, ForeignKey("item.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    unit = Column(String(50), nullable=False)
    detail_type = Column(String(50), nullable=False, index=True)

    details = Column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
        server_default="{}",
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    outbound_order = relationship("OutboundOrder", foreign_keys=[outbound_order_id], lazy="joined")
    item = relationship("Item", foreign_keys=[item_id], lazy="joined")
    allocations = relationship(
        "OutboundOrderAllocation",
        back_populates="outbound_order_detail",
        lazy="selectin",
    )

    status = column_property(_outbound_detail_status_expr(id, quantity))

class OutboundOrderAllocation(Base):
    """Outbound order allocation."""

    __tablename__ = "outbound_order_allocation"
    id = Column(Integer, primary_key=True, index=True)
    outbound_order_detail_id = Column(Integer, ForeignKey("outbound_order_detail.id"), nullable=False, index=True)
    item_stock_id = Column(Integer, ForeignKey("item_stock.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=0)
    status = Column(String(20), default="initialize", nullable=False, index=True)
    from_location_id = Column(Integer, ForeignKey("location.id"), nullable=True, index=True)
    to_location_id = Column(Integer, ForeignKey("location.id"), nullable=True, index=True)
    allocation_type = Column(String(20), default="outbound", nullable=False, index=True)
    robot_task_id = Column(Integer, ForeignKey("robot_task.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    outbound_order_detail = relationship(
        "OutboundOrderDetail",
        foreign_keys=[outbound_order_detail_id],
        back_populates="allocations",
        lazy="joined",
    )
    robot_task = relationship("RobotTask", foreign_keys=[robot_task_id], lazy="joined")
    item_stock = relationship("ItemStock", foreign_keys=[item_stock_id], lazy="joined")
    from_location = relationship("Location", foreign_keys=[from_location_id], lazy="joined")
    to_location = relationship("Location", foreign_keys=[to_location_id], lazy="joined")