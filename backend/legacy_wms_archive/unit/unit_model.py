from sqlalchemy import Column, DateTime, Integer, String, func, Text, Numeric
from app.core.database import Base
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey

class Unit(Base):
    __tablename__ = "unit"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class ItemUnit(Base):
    __tablename__ = "item_unit"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("item.id"), nullable=False, index=True)
    unit_id = Column(Integer, ForeignKey("unit.id"), nullable=False, index=True)
    conversion_factor = Column(Numeric(12, 4), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    item = relationship("Item", foreign_keys=[item_id], lazy="joined")
    unit = relationship("Unit", foreign_keys=[unit_id], lazy="joined")