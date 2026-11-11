"""Audit / action log tables and the IP -> device name registry.

``user_id`` has no FK on purpose: users are hard-deleted, log rows must survive.
"""
from sqlalchemy import BigInteger, Boolean, Column, DateTime, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class Device(Base):
    """Static-IP device registry (PDA / TV / PC) used to resolve ``device_name`` from IP."""

    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(45), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    device_type = Column(String(20), nullable=False, default="pda")
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AuditLog(Base):
    """Authentication / authorization events (no payload)."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_user_created", "user_id", "created_at"),
        Index("ix_audit_logs_event_created", "event_type", "created_at"),
    )

    id = Column(BigInteger, primary_key=True)
    event_type = Column(String(30), nullable=False)
    result = Column(String(10), nullable=False)
    failure_reason = Column(String(50), nullable=True)
    user_id = Column(Integer, nullable=True)
    username = Column(String(50), nullable=True)
    ip = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    device_type = Column(String(20), nullable=True)
    device_name = Column(String(100), nullable=True)
    request_id = Column(String(64), nullable=True)
    path = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class ActionLog(Base):
    """Business actions: every non-GET request made by an authenticated user."""

    __tablename__ = "action_logs"
    __table_args__ = (
        Index("ix_action_logs_user_created", "user_id", "created_at"),
        Index("ix_action_logs_action_created", "action", "created_at"),
    )

    id = Column(BigInteger, primary_key=True)
    user_id = Column(Integer, nullable=True)
    username = Column(String(50), nullable=True)
    action = Column(String(100), nullable=True)
    method = Column(String(10), nullable=False)
    route_template = Column(String(255), nullable=True)
    path = Column(String(255), nullable=False)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String(50), nullable=True)
    status_code = Column(Integer, nullable=False)
    result = Column(String(10), nullable=False)
    error_message = Column(Text, nullable=True)
    payload = Column(JSONB, nullable=True)
    query_params = Column(JSONB, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    ip = Column(String(45), nullable=True)
    device_type = Column(String(20), nullable=True)
    device_name = Column(String(100), nullable=True)
    request_id = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
