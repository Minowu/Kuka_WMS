from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    case,
    exists,
    func,
    select,
    text,
)
from sqlalchemy.orm import column_property, relationship

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
    )

    id = Column(Integer, primary_key=True, index=True)
    # Map nodeUuid from KUKA floor map.
    location_code = Column(String(100), nullable=False, index=True)
    # Map nodeLabel / display name (e.g. '51', '216').
    location_name = Column(String(100), nullable=False, index=True)
    function_type = Column(Integer, nullable=True, default=2)  # 2: Rack node
    location_type = Column(
        String(30),
        nullable=False,
        default="UNASSIGNED",
        server_default="UNASSIGNED",
    )  # UNASSIGNED, RAW_MATERIAL, CNC_SLOT, WASHING_SLOT, EMPTY_CART_BUFFER
    machine_id = Column(
        Integer,
        ForeignKey("machine.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    position_index = Column(Integer, nullable=True)  # 1, 2, or 3 for CNC stations
    map_x = Column(Integer, nullable=True)
    map_y = Column(Integer, nullable=True)
    warehouse_id = Column(
        Integer,
        ForeignKey("warehouse.id"),
        nullable=False,
        index=True,
    )
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    occupied_quantity = column_property(
        select(func.coalesce(func.sum(ItemStock.quantity), 0))
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
    machine = relationship("Machine", back_populates="locations", lazy="joined")
    stocks = relationship(
        "ItemStock",
        primaryjoin="Location.id == ItemStock.location_id",
        foreign_keys="[ItemStock.location_id]",
        back_populates="location",
        lazy="selectin",
    )

    @property
    def zone_id(self):
        return None


class WarehouseMap(Base):
    __tablename__ = "warehouse_map"

    id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(
        Integer,
        ForeignKey("warehouse.id"),
        nullable=False,
        index=True,
    )
    source = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True, nullable=False)

    warehouse = relationship("Warehouse", lazy="joined")

    @property
    def zone_id(self):
        return None
