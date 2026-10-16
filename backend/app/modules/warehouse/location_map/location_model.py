from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func,
    select, case, exists, or_, text,
)
from sqlalchemy.orm import relationship, column_property
from app.core.database import Base
from app.modules.warehouse.item_stock.item_stock_model import (
    ItemStock,
    countable_stock_level_criterion,
    positive_stock_quantity_criterion,
)
def _location_status_expression(location_id_col):
    return case(
        (
            exists(
                select(1)
                .where(
                    ItemStock.location_id == location_id_col,
                    ItemStock.quantity > 0,
                    ItemStock.is_active.is_(True),
                )
                .correlate_except(ItemStock)
            ),
            "has_stock",
        ),
        (
            exists(
                select(1)
                .where(
                    ItemStock.destination_location_id == location_id_col,
                    ItemStock.is_locked.is_(True),
                    ItemStock.is_active.is_(True),
                )
                .correlate_except(ItemStock)
            ),
            "reserved",
        ),
        else_="empty",
    )


class Location(Base):
    """Warehouse location model for storing materials and products."""

    __tablename__ = "location"
    __table_args__ = (
        UniqueConstraint(
            "warehouse_id",
            "location_code",
            name="uq_location_warehouse_code",
        ),
        Index(
            "uq_location_warehouse_bin",
            "warehouse_id",
            "bin_code",
            unique=True,
            postgresql_where=text("bin_code IS NOT NULL"),
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    # Map node number. Rewritten on every import because map editors renumber nodes.
    location_code = Column(String(50), nullable=False, index=True)
    location_name = Column(String(100), nullable=False, index=True)
    # Physical bin label (e.g. KH1.13). Stable identity used to match across imports.
    bin_code = Column(String(50), nullable=True, index=True)
    row = Column(String(10))  # Mapped from DB 'row' column
    column = Column("column", String(10))  # 'column' is SQL keyword, use mapped name
    level = Column(String(10))
    node_name = Column(String(50))  # Additional node identifier
    location_type = Column(String(30), nullable=False, default="CNC_SLOT", server_default="CNC_SLOT")  # RAW_MATERIAL, CNC_SLOT, WASHING_SLOT, EMPTY_CART_BUFFER
    machine_code = Column(String(50), nullable=True, index=True)  # E.g. 'CNC-01'
    position_index = Column(Integer, nullable=True)  # 1 or 2 for CNC stations
    default_stage_level = Column(
        Integer,
        nullable=True,
        index=True,
        doc="Quy định vị trí thuộc công đoạn CNC Level mấy (1, 2, 3...); NULL nếu là trạm chung hoặc vùng khác",
    )
    map_x = Column(Integer, nullable=True)
    map_y = Column(Integer, nullable=True)
    warehouse_id = Column(
        Integer,
        ForeignKey("warehouse.id"),
        nullable=False,
        index=True,
    )
    zone_id = Column(
        Integer,
        ForeignKey("zone.id"),
        nullable=True,
        index=True,
    )
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    occupied_quantity = column_property(
        select(
            func.coalesce(
                func.sum(ItemStock.quantity),
                0
            )
        )
        .where(
            ItemStock.location_id == id,
            ItemStock.is_active.is_(True),
            countable_stock_level_criterion(),
            positive_stock_quantity_criterion(),
        )
        .correlate_except(ItemStock)
        .scalar_subquery()
    )

    status = column_property(_location_status_expression(id))

    warehouse = relationship("Warehouse", lazy="joined")
    zone = relationship("Zone", lazy="joined")
    stocks = relationship(
        "ItemStock",
        primaryjoin="Location.id == ItemStock.location_id",
        foreign_keys="[ItemStock.location_id]",
        back_populates="location",
        lazy="selectin"
    )


class WarehouseMap(Base):
    __tablename__ = "warehouse_map"

    id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(
        Integer,
        ForeignKey("warehouse.id"),
        nullable=False,
        index=True,
    )
    zone_id = Column(
        Integer,
        ForeignKey("zone.id"),
        nullable=True,
        index=True,
    )
    source = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True, nullable=False)

    zone = relationship("Zone", lazy="joined")
    warehouse = relationship("Warehouse", lazy="joined")
