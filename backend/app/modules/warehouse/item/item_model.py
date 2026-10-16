"""Item model for warehouse inventory."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, BigInteger, JSON, String, Text, func, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.orm import column_property
from app.core.config import settings

from app.core.database import Base
from app.modules.warehouse.item_stock.item_stock_model import (
    ItemStock,
    countable_stock_level_criterion,
    positive_stock_quantity_criterion,
)
from app.modules.warehouse.location_map.location_model import Location
from app.modules.warehouse.warehouse_zone.warehouse_model import Zone


class Item(Base):
    """Item master data - represents physical items in warehouse."""

    __tablename__ = "item"
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    base_quantity = Column(BigInteger, nullable=False, default=1, server_default="1")
    standard_quantity_per_cart = Column(Integer, nullable=False, default=120, server_default="120")
    base_unit_id = Column("base_unit", Integer, nullable=True)
    max_quantity = Column(Integer, nullable=True, default=999999)
    min_quantity = Column(Integer, nullable=True, default=0)
    is_active = Column(Boolean, default=True, nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouse.id"), nullable=False, index=True)
    details = Column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
        server_default="{}",
    )
    supplier = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    warehouse = relationship("Warehouse", lazy="joined")

    quantity = column_property(
        select(func.coalesce(func.sum(ItemStock.quantity), 0))
        .where(
            ItemStock.item_id == id,
            ItemStock.is_active.is_(True),
            countable_stock_level_criterion(),
            positive_stock_quantity_criterion(),
            ItemStock.location_id.in_(
                select(Location.id)
                .join(Zone, Location.zone_id == Zone.id)
                .where(
                    Location.warehouse_id == warehouse_id,
                    Location.is_active.is_(True),
                    Zone.code.in_(settings.zone_storage),
                )
                .correlate_except(Location, Zone)
            ),
        )
        .correlate_except(ItemStock)
        .scalar_subquery()
    )

class QR_Code(Base):
    __tablename__ = "qr_code"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("item.id"), nullable=False, index=True)
    item_stock_id = Column(Integer, ForeignKey("item_stock.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    qr_type = Column(String(50), nullable=False, default="item")

    item = relationship("Item", lazy="joined")
    item_stock = relationship("ItemStock", foreign_keys=[item_stock_id], lazy="joined")