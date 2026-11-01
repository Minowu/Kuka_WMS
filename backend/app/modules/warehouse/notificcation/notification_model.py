"""Notification model (decommissioned - kept as abstract placeholder)."""

from sqlalchemy import Column, DateTime, Integer, String, Text, func
from app.core.database import Base


class Notification(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True)
    warehouse_id = Column(Integer)
    title = Column(String(255))
    message = Column(Text)
    action = Column(String(255))
    notification_type = Column(String(50), default="alert")
    status = Column(String(50), default="unsolved")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())