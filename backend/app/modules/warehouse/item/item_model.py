"""Item model for warehouse / CNC production inventory."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import column_property, relationship

from app.core.database import Base
from app.modules.warehouse.item_stock.item_stock_model import (
    ItemStock,
    countable_stock_level_criterion,
    positive_stock_quantity_criterion,
)
from app.modules.warehouse.location_map.location_model import Location


class Item(Base):
    """Item master data - represents product models / workpieces in CNC production."""

    __tablename__ = "item"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    standard_quantity_per_cart = Column(Integer, nullable=False, default=120, server_default="120")
    base_unit_id = Column("base_unit", Integer, nullable=True)
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

    @property
    def unit_id(self):
        return self.base_unit_id

    @unit_id.setter
    def unit_id(self, value):
        self.base_unit_id = value

    quantity = column_property(
        select(func.coalesce(func.sum(ItemStock.quantity), 0))
        .where(
            ItemStock.item_id == id,
            ItemStock.is_active.is_(True),
            countable_stock_level_criterion(),
            positive_stock_quantity_criterion(),
            ItemStock.location_id.in_(
                select(Location.id)
                .where(
                    Location.warehouse_id == warehouse_id,
                    Location.is_active.is_(True),
                )
                .correlate_except(Location)
            ),
        )
        .correlate_except(ItemStock)
        .scalar_subquery()
    )