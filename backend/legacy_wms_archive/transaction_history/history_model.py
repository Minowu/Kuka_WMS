from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, func, JSON, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from sqlalchemy.dialects.postgresql import JSONB

class Transaction(Base):
    __tablename__ = "transaction"

    id = Column(Integer, primary_key=True, index=True)
    from_location_id = Column(Integer, ForeignKey("location.id"), nullable=False, index=True)
    to_location_id = Column(Integer, ForeignKey("location.id"), nullable=False, index=True)
    transaction_type = Column(String(50), nullable=False, index=True)
    item_stock_id = Column(Integer, ForeignKey("item_stock.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    from_location = relationship("Location", foreign_keys=[from_location_id], lazy="joined")
    to_location = relationship("Location", foreign_keys=[to_location_id], lazy="joined")
    item_stock = relationship("ItemStock", lazy="joined")
    created_by = relationship("User", foreign_keys=[created_by_id], lazy="joined")

class History(Base):
    __tablename__ = "history"

    id = Column(Integer, primary_key=True, index=True)
    inbound_order_id = Column(Integer, ForeignKey("inbound_order.id"), nullable=True, index=True)
    outbound_order_id = Column(Integer, ForeignKey("outbound_order.id"), nullable=True, index=True)
    old_status = Column(String(50), nullable=False, index=True)
    new_status = Column(String(50), nullable=False, index=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    description = Column(Text, nullable=False)
    details = Column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
        server_default="{}",
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    inbound_order = relationship("InboundOrder", foreign_keys=[inbound_order_id], lazy="joined")
    outbound_order = relationship("OutboundOrder", foreign_keys=[outbound_order_id], lazy="joined")
    created_by = relationship("User", foreign_keys=[created_by_id], lazy="joined")