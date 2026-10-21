"""Item stock model for warehouse cell inventory (WIP Containers / Racks)."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Boolean,
    func,
    literal,
)
from sqlalchemy.orm import relationship, synonym
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.core.database import Base


class ItemStock(Base):
    """Current item stock rows stored in warehouse locations (WIP Containers / Racks)."""

    __tablename__ = "item_stock"

    id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True, default=uuid.uuid4)
    container_code = Column(String(50), unique=True, nullable=True, index=True)
    item_id = Column("item_id", Integer, ForeignKey("item.id"), nullable=False, index=True)
    location_id = Column(
        "location_id",
        Integer,
        ForeignKey("location.id"),
        nullable=True,
        index=True,
    )
    destination_location_id = Column(
        Integer,
        ForeignKey("location.id"),
        nullable=True,
        index=True,
    )
    quantity = Column(Numeric(12, 3), nullable=False, default=0)
    current_stage_level = Column(Integer, nullable=False, default=0, server_default="0", index=True)
    is_locked = Column(Boolean, nullable=False, default=False, server_default="false", index=True)
    locked_by_mission_code = Column(String(100), nullable=True)
    fleet_registered = Column(Boolean, nullable=False, default=False, server_default="false")

    status = Column(
        String(20),
        nullable=False,
        default="available",
        server_default="available",
        index=True,
    )
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    available_quantity = synonym("quantity")

    item = relationship("Item", lazy="joined")
    location = relationship(
        "Location",
        lazy="joined",
        foreign_keys=[location_id],
        back_populates="stocks",
    )
    destination_location = relationship(
        "Location",
        lazy="joined",
        foreign_keys=[destination_location_id],
    )

    __table_args__ = (
        CheckConstraint(
            "quantity >= 0",
            name="check_item_stock_quantity_non_negative",
        ),
    )


def countable_stock_level_criterion(stock_level_col=None):
    """All active mechanical cart stocks are countable (stock_level column pruned)."""
    return literal(True)


def positive_stock_quantity_criterion(quantity_col=None):
    """Depleted stock rows (quantity = 0) are excluded from inventory read views."""
    if quantity_col is None:
        quantity_col = ItemStock.quantity
    return quantity_col > 0
